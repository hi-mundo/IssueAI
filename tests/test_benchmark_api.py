from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from issueai.benchmark import load_json


class BenchmarkApiTests(unittest.TestCase):
    def test_load_json_reads_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "payload.json"
            payload = {"id": "cp-123", "repository": "example/repo"}
            path.write_text(json.dumps(payload))

            self.assertEqual(load_json(path), payload)


if __name__ == "__main__":
    unittest.main()
