from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from issueai.core import HistoricalEvalRuntime, write_product_understanding


class HistoricalEvalRuntimeTests(unittest.TestCase):
    def test_write_product_understanding_emits_json_document(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "product-understanding.json"
            payload = {"product": "IssueAI", "capabilities": ["plugin", "byok"]}

            write_product_understanding(output_path, payload)

            self.assertEqual(json.loads(output_path.read_text()), payload)
            self.assertTrue(output_path.read_text().endswith("\n"))

    def test_runtime_descriptor_keeps_paths_explicit(self) -> None:
        runtime = HistoricalEvalRuntime(
            repo_root=Path("/tmp/repo"),
            runtime_root=Path("/tmp/runtime"),
            graph_path=Path("/tmp/graph.json"),
        )

        self.assertEqual(runtime.repo_root, Path("/tmp/repo"))
        self.assertEqual(runtime.runtime_root, Path("/tmp/runtime"))
        self.assertEqual(runtime.graph_path, Path("/tmp/graph.json"))


if __name__ == "__main__":
    unittest.main()
