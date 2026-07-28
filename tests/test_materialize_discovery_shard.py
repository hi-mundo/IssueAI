import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class MaterializeDiscoveryShardScriptTests(unittest.TestCase):
    def test_invalid_shard_returns_deterministic_json_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            plan_path = root / "plan.json"
            output_path = root / "out.json"
            script_path = Path(__file__).resolve().parents[1] / "issueai" / "bug_hunt_runtime" / "scripts" / "materialize_discovery_shard.py"

            plan_path.write_text(
                json.dumps(
                    {
                        "shards": [[]],
                        "inventory": [],
                        "branches": [],
                        "coverage_rows": [],
                    }
                )
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--repo",
                    str(root),
                    "--plan",
                    str(plan_path),
                    "--shard",
                    "9",
                    "--output",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).resolve().parents[1],
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["error"], "SHARD_OUT_OF_RANGE")
            self.assertEqual(payload["shard"], 9)
            self.assertEqual(payload["available"], 1)


if __name__ == "__main__":
    unittest.main()
