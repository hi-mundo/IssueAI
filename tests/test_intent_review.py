import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from issueai.core import (
    load_issue_hunt_gate,
    load_repository_intent_review_gate,
    preflight_repository,
    run_issue_hunt,
    run_issue_probe,
    run_repository_intent_review,
    run_repository_recon,
)


def init_git_repo(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "issueai@example.invalid"], cwd=root, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "IssueAI Tests"], cwd=root, capture_output=True, check=True)


class RepositoryWorkflowTests(unittest.TestCase):
    def test_preflight_creates_issueai_layout_and_gitignore(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            init_git_repo(root)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("def run():\n    return 1\n")

            payload = preflight_repository(root)

            self.assertEqual(payload["status"], "initial")
            self.assertTrue((root / ".issueai" / "snapshots" / "latest.json").exists())
            self.assertTrue((root / ".issueai" / "metadata" / "repo-profile.json").exists())
            self.assertIn(".issueai/", (root / ".gitignore").read_text())

    def test_repository_recon_creates_graph_and_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            init_git_repo(root)
            (root / "app").mkdir()
            (root / "app" / "main.py").write_text("from app.service import run\n\nrun()\n")
            (root / "app" / "service.py").write_text("def run(value: int = 1) -> int:\n    return value\n")

            payload = run_repository_recon(root, repository_label=root.name)

            self.assertTrue(payload["nextStepGate"]["ready"])
            self.assertTrue((root / ".issueai" / "understanding" / "repository-recon.json").exists())
            self.assertTrue((root / ".issueai" / "graphs" / "repository-recon-graph.json").exists())
            self.assertIn("applicationMap", payload["understanding"])
            self.assertIn("workflow", payload)

    def test_repository_intent_review_requires_recon(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            init_git_repo(root)
            (root / "pkg").mkdir()
            (root / "pkg" / "service.py").write_text("def run(value: int) -> int:\n    return value + 1\n")

            payload = run_repository_intent_review(root, repository_label=root.name)

            self.assertFalse(payload["nextStepGate"]["ready"])
            self.assertIn("Repository Recon has not run yet.", payload["nextStepGate"]["blockers"])

    def test_full_chain_reaches_issue_probe_on_clean_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            init_git_repo(root)
            (root / "pkg").mkdir()
            (root / "pkg" / "service.py").write_text("def run(value: int) -> int:\n    return value + 1\n")
            (root / "pkg" / "schema.py").write_text("class InputSchema:\n    pass\n")

            recon = run_repository_recon(root, repository_label=root.name)
            review = run_repository_intent_review(root, repository_label=root.name, purpose_hint="review this service")
            hunt = run_issue_hunt(root, repository_label=root.name)
            probe = run_issue_probe(root, repository_label=root.name)

            self.assertTrue(recon["nextStepGate"]["ready"])
            self.assertTrue(review["nextStepGate"]["ready"], review["nextStepGate"])
            self.assertGreater(len(hunt["hypotheses"]), 0)
            self.assertGreaterEqual(len(probe["verdicts"]), 1)
            state = json.loads((root / ".issueai" / "state.json").read_text())
            self.assertTrue(state["repositoryIntentReview"]["issueHuntReady"])
            self.assertTrue(state["issueHunt"]["issueProbeReady"])

    def test_contract_import_counts_as_explicit_schema_signal(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            init_git_repo(root)
            (root / "pkg").mkdir()
            (root / "pkg" / "contracts.py").write_text("from typing import TypedDict\n\nclass InputContract(TypedDict):\n    value: int\n")
            (root / "pkg" / "routes.py").write_text(
                "from .contracts import InputContract\n\n"
                "def run(payload: InputContract) -> int:\n"
                "    return payload['value']\n"
            )

            run_repository_recon(root, repository_label=root.name)
            review = run_repository_intent_review(root, repository_label=root.name)

            schema_gap_paths = [item["path"] for item in review["findings"]["findings"] if item["type"] == "schema-gap"]
            self.assertNotIn("pkg/routes.py", schema_gap_paths)

    def test_nested_generic_params_do_not_trigger_false_typing_gap(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            init_git_repo(root)
            (root / "pkg").mkdir()
            (root / "pkg" / "schema.py").write_text("class InputSchema:\n    pass\n")
            (root / "pkg" / "service.py").write_text(
                "from typing import Callable, Optional\n\n"
                "def run(values: tuple[str, int], callback: Optional[Callable[[str, int], None]] = None) -> tuple[str, int]:\n"
                "    if callback is not None:\n"
                "        callback(*values)\n"
                "    return values\n"
            )

            run_repository_recon(root, repository_label=root.name)
            review = run_repository_intent_review(root, repository_label=root.name)

            typing_gap_paths = [item["path"] for item in review["findings"]["findings"] if item["type"] == "typing-gap"]
            self.assertNotIn("pkg/service.py", typing_gap_paths)

    def test_issue_hunt_gate_reports_blockers_before_repository_intent_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            init_git_repo(root)
            (root / "pkg").mkdir()
            (root / "pkg" / "service.py").write_text("def run(value: int) -> int:\n    return value + 1\n")

            run_repository_recon(root, repository_label=root.name)
            gate = load_issue_hunt_gate(root)

            self.assertFalse(gate["ready"])
            self.assertIn("Repository Intent Review has not run yet.", gate["blockers"])

    def test_preflight_marks_changed_subset_as_partially_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            init_git_repo(root)
            (root / "app").mkdir()
            (root / "tests").mkdir()
            (root / "app" / "schema.py").write_text("class InputSchema:\n    pass\n")
            (root / "app" / "service.py").write_text("def run(value: int) -> int:\n    return value + 1\n")
            (root / "tests" / "test_smoke.py").write_text("def test_smoke() -> None:\n    assert True\n")

            run_repository_recon(root, repository_label=root.name)
            run_repository_intent_review(root, repository_label=root.name)

            (root / "app" / "service.py").write_text("def run(value: int) -> int:\n    result = value + 2\n    return result\n")

            snapshot = preflight_repository(root)
            recon_freshness = snapshot["artifactFreshness"]["repositoryRecon"]
            review_freshness = snapshot["artifactFreshness"]["repositoryIntentReview"]

            self.assertEqual(snapshot["status"], "partial-stale")
            self.assertEqual(recon_freshness["status"], "partial-stale")
            self.assertEqual(review_freshness["status"], "partial-stale")
            self.assertIn("app", recon_freshness["staleDomains"])
            self.assertIn("app", review_freshness["staleDomains"])
            self.assertIn("tests", recon_freshness["freshDomains"])

    def test_repository_intent_review_gate_blocks_when_recon_subset_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            init_git_repo(root)
            (root / "app").mkdir()
            (root / "tests").mkdir()
            (root / "app" / "schema.py").write_text("class InputSchema:\n    pass\n")
            (root / "app" / "service.py").write_text("def run(value: int) -> int:\n    return value + 1\n")
            (root / "tests" / "test_smoke.py").write_text("def test_smoke() -> None:\n    assert True\n")

            run_repository_recon(root, repository_label=root.name)
            run_repository_intent_review(root, repository_label=root.name)

            (root / "app" / "service.py").write_text("def run(value: int) -> int:\n    result = value + 2\n    return result\n")

            gate = load_repository_intent_review_gate(root)

            self.assertFalse(gate["ready"])
            self.assertTrue(any("Repository Recon must be refreshed for domains: app." in blocker for blocker in gate["blockers"]))

    def test_preflight_does_not_acknowledge_stale_subset_without_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            init_git_repo(root)
            (root / "app").mkdir()
            (root / "tests").mkdir()
            (root / "app" / "schema.py").write_text("class InputSchema:\n    pass\n")
            (root / "app" / "service.py").write_text("def run(value: int) -> int:\n    return value + 1\n")
            (root / "tests" / "test_smoke.py").write_text("def test_smoke() -> None:\n    assert True\n")

            run_repository_recon(root, repository_label=root.name)
            run_repository_intent_review(root, repository_label=root.name)

            (root / "app" / "service.py").write_text("def run(value: int) -> int:\n    result = value + 2\n    return result\n")

            first = preflight_repository(root)
            second = preflight_repository(root)

            self.assertEqual(first["status"], "partial-stale")
            self.assertEqual(second["status"], "partial-stale")
            self.assertIn("app", first["artifactFreshness"]["repositoryRecon"]["staleDomains"])
            self.assertIn("app", second["artifactFreshness"]["repositoryRecon"]["staleDomains"])

    def test_subset_refresh_updates_coverage_to_changed_domain(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            init_git_repo(root)
            (root / "app").mkdir()
            (root / "tests").mkdir()
            (root / "app" / "schema.py").write_text("class InputSchema:\n    pass\n")
            (root / "app" / "service.py").write_text("def run(value: int) -> int:\n    return value + 1\n")
            (root / "tests" / "test_smoke.py").write_text("def test_smoke() -> None:\n    assert True\n")

            run_repository_recon(root, repository_label=root.name)
            run_repository_intent_review(root, repository_label=root.name)

            (root / "app" / "service.py").write_text("def run(value: int) -> int:\n    result = value + 2\n    return result\n")

            recon = run_repository_recon(root, repository_label=root.name)
            review = run_repository_intent_review(root, repository_label=root.name)
            snapshot = preflight_repository(root)

            self.assertEqual(recon["understanding"]["checksumMetadata"]["coveredDomains"], ["app"])
            self.assertEqual(review["understanding"]["checksumMetadata"]["coveredDomains"], ["app"])
            self.assertTrue(all(path.startswith("app/") for path in review["understanding"]["criticalPaths"]))
            self.assertEqual(snapshot["artifactFreshness"]["repositoryRecon"]["status"], "fresh")
            self.assertEqual(snapshot["artifactFreshness"]["repositoryIntentReview"]["status"], "fresh")

    def test_issue_hunt_refreshes_captured_at_on_each_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            init_git_repo(root)
            (root / "pkg").mkdir()
            (root / "pkg" / "service.py").write_text("def run(value: int) -> int:\n    return value + 1\n")
            (root / "pkg" / "schema.py").write_text("class InputSchema:\n    pass\n")

            run_repository_recon(root, repository_label=root.name)
            run_repository_intent_review(root, repository_label=root.name)

            with patch(
                "issueai.core.issue_hunt.utc_now",
                side_effect=[
                    "2026-07-28T18:30:00+00:00",
                    "2026-07-28T18:31:00+00:00",
                ],
            ):
                first = run_issue_hunt(root, repository_label=root.name)
                second = run_issue_hunt(root, repository_label=root.name)

            self.assertEqual(first["nextStepGate"]["issueHunt"]["updatedAt"], "2026-07-28T18:30:00+00:00")
            self.assertEqual(second["nextStepGate"]["issueHunt"]["updatedAt"], "2026-07-28T18:31:00+00:00")

            artifact = json.loads((root / ".issueai" / "findings" / "issue-hunt-hypotheses.json").read_text())
            state = json.loads((root / ".issueai" / "state.json").read_text())
            self.assertEqual(artifact["capturedAt"], "2026-07-28T18:31:00+00:00")
            self.assertEqual(state["issueHunt"]["updatedAt"], "2026-07-28T18:31:00+00:00")

    def test_issue_probe_refreshes_captured_at_on_each_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            init_git_repo(root)
            (root / "pkg").mkdir()
            (root / "pkg" / "service.py").write_text("def run(value: int) -> int:\n    return value + 1\n")
            (root / "pkg" / "schema.py").write_text("class InputSchema:\n    pass\n")

            run_repository_recon(root, repository_label=root.name)
            run_repository_intent_review(root, repository_label=root.name)
            run_issue_hunt(root, repository_label=root.name)

            with patch(
                "issueai.core.issue_probe.utc_now",
                side_effect=[
                    "2026-07-28T18:40:00+00:00",
                    "2026-07-28T18:41:00+00:00",
                ],
            ):
                first = run_issue_probe(root, repository_label=root.name)
                second = run_issue_probe(root, repository_label=root.name)

            self.assertGreaterEqual(len(first["verdicts"]), 1)
            self.assertGreaterEqual(len(second["verdicts"]), 1)

            artifact = json.loads((root / ".issueai" / "findings" / "issue-probe-results.json").read_text())
            state = json.loads((root / ".issueai" / "state.json").read_text())
            self.assertEqual(artifact["capturedAt"], "2026-07-28T18:41:00+00:00")
            self.assertEqual(state["issueProbe"]["updatedAt"], "2026-07-28T18:41:00+00:00")

    def test_cli_repository_workflow_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            init_git_repo(root)
            (root / "pkg").mkdir()
            (root / "pkg" / "service.py").write_text("def run(value: int) -> int:\n    return value + 1\n")
            (root / "pkg" / "schema.py").write_text("class InputSchema:\n    pass\n")

            repo_recon = subprocess.run(
                [sys.executable, "-m", "issueai.cli", "repository-recon", "--repo", str(root)],
                capture_output=True,
                text=True,
                cwd=Path(__file__).resolve().parents[1],
            )
            self.assertEqual(repo_recon.returncode, 0, repo_recon.stderr)
            self.assertIn("applicationMap", json.loads(repo_recon.stdout)["understanding"])

            intent_review = subprocess.run(
                [sys.executable, "-m", "issueai.cli", "repository-intent-review", "--repo", str(root)],
                capture_output=True,
                text=True,
                cwd=Path(__file__).resolve().parents[1],
            )
            self.assertEqual(intent_review.returncode, 0, intent_review.stderr)
            self.assertIn("nextStepGate", json.loads(intent_review.stdout))

            issue_hunt = subprocess.run(
                [sys.executable, "-m", "issueai.cli", "issue-hunt", "--repo", str(root)],
                capture_output=True,
                text=True,
                cwd=Path(__file__).resolve().parents[1],
            )
            self.assertEqual(issue_hunt.returncode, 0, issue_hunt.stderr)
            self.assertIn("hypotheses", json.loads(issue_hunt.stdout))
