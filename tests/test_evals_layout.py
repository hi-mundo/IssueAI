import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class IssueAIEvalsLayoutTest(unittest.TestCase):
    def test_official_manifest_has_20_cases(self) -> None:
        manifest = json.loads((ROOT / "evals" / "unmapped-repositories-20.json").read_text())
        self.assertEqual(len(manifest["cases"]), 20)

    def test_dataset_catalog_registers_current_batch(self) -> None:
        catalog = json.loads((ROOT / "evals" / "datasets" / "catalog.json").read_text())
        datasets = {entry["id"]: entry for entry in catalog["datasets"]}
        self.assertIn("historical-route-20-v1", datasets)
        self.assertEqual(datasets["historical-route-20-v1"]["case_count"], 20)
        self.assertIn("historical-route-20-v2", datasets)
        self.assertEqual(datasets["historical-route-20-v2"]["status"], "proposed-from-artifacts")
        self.assertEqual(datasets["historical-route-20-v2"]["case_count"], 20)

    def test_reserved_batch_two_structure_exists(self) -> None:
        batch_root = ROOT / "evals" / "datasets" / "historical-route-20-v2"
        self.assertTrue((batch_root / "README.md").exists())
        self.assertTrue((batch_root / "NOTES.md").exists())
        self.assertTrue((batch_root / "manifest.json").exists())
        self.assertTrue((batch_root / "ground-truth.proposed.json").exists())

    def test_promptfoo_harness_exists(self) -> None:
        self.assertTrue((ROOT / "evals" / "promptfoo" / "promptfooconfig.yaml").exists())
        self.assertTrue((ROOT / "evals" / "promptfoo" / "provider.js").exists())
        self.assertTrue((ROOT / "evals" / "promptfoo" / "tests.yaml").exists())

    def test_vendored_bug_hunt_runtime_exists(self) -> None:
        runtime_root = ROOT / "issueai" / "bug_hunt_runtime"
        self.assertTrue((runtime_root / "scripts" / "query_issue_evidence_graph.py").exists())
        self.assertTrue((runtime_root / "scripts" / "build_intelligent_discovery_plan.py").exists())
