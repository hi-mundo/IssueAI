import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from issueai.core import (
    load_issue_hunt_gate,
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
