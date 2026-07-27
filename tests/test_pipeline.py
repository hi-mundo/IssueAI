import json
import subprocess
import sys
import unittest
from pathlib import Path

from issueai.core import IssueAIRequest, run_pipeline
from issueai.hosts import default_host_plugins
from issueai.providers import default_providers


ROOT = Path(__file__).resolve().parents[1]


class IssueAIPipelineTest(unittest.TestCase):
    def test_pipeline_promotes_lifecycle_from_runtime_signals(self) -> None:
        payload = run_pipeline(
            IssueAIRequest(
                repository="example/repo",
                surfaces=("runtime", "session"),
                local_signals=("async", "timeout", "retry", "log"),
            )
        )
        ordered = payload["plan"]["ordered_mechanisms"]
        self.assertIn("lifecycle", ordered)
        self.assertIn("state_reuse", ordered)
        self.assertIn("observability", ordered)

    def test_host_registry_is_host_first(self) -> None:
        hosts = default_host_plugins()
        self.assertEqual(hosts[0].host, "codex")
        self.assertTrue(any(entry.host == "cursor" for entry in hosts))

    def test_provider_registry_keeps_host_primary(self) -> None:
        providers = default_providers()
        self.assertEqual(providers[0].name, "host")
        self.assertTrue(providers[0].primary)

    def test_cli_prints_json_pipeline(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "issueai.cli",
                "--repository",
                "example/repo",
                "--signal",
                "async",
                "--signal",
                "timeout",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["request"]["repository"], "example/repo")
        self.assertIn("lifecycle", payload["plan"]["ordered_mechanisms"])
