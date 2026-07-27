import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class IssueAIEvalsLayoutTest(unittest.TestCase):
    def test_official_manifest_has_20_cases(self) -> None:
        manifest = json.loads((ROOT / "evals" / "unmapped-repositories-20.json").read_text())
        self.assertEqual(len(manifest["cases"]), 20)

    def test_promptfoo_harness_exists(self) -> None:
        self.assertTrue((ROOT / "evals" / "promptfoo" / "promptfooconfig.yaml").exists())
        self.assertTrue((ROOT / "evals" / "promptfoo" / "provider.js").exists())
        self.assertTrue((ROOT / "evals" / "promptfoo" / "tests.yaml").exists())

    def test_vendored_bug_hunt_runtime_exists(self) -> None:
        runtime_root = ROOT / "issueai" / "bug_hunt_runtime"
        self.assertTrue((runtime_root / "scripts" / "query_issue_evidence_graph.py").exists())
        self.assertTrue((runtime_root / "scripts" / "build_intelligent_discovery_plan.py").exists())
