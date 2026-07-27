import unittest
from pathlib import Path

from issueai import __version__
from issueai.adapters import ClaudeAdapter, CodexAdapter
from issueai.core import IssueAIModel


ROOT = Path(__file__).resolve().parents[1]


class IssueAIImportsTest(unittest.TestCase):
    def test_version_present(self) -> None:
        self.assertEqual(__version__, "0.1.0")

    def test_model_contains_benchmark_summary(self) -> None:
        model = IssueAIModel()
        self.assertEqual(model.name, "IssueAI")
        self.assertEqual(model.benchmark_summary["top100_recall"], "20/20")

    def test_adapters_expose_host_descriptions(self) -> None:
        self.assertEqual(CodexAdapter.describe()["host"], "codex")
        self.assertEqual(ClaudeAdapter.describe()["host"], "claude")

    def test_top_level_docs_exist(self) -> None:
        self.assertTrue((ROOT / "README.md").exists())
        self.assertTrue((ROOT / "USAGE.md").exists())
        self.assertTrue((ROOT / "IMPLEMENTATION.md").exists())
        self.assertTrue((ROOT / "PAPER.md").exists())
        self.assertTrue((ROOT / "TODO.md").exists())


if __name__ == "__main__":
    unittest.main()
