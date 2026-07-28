import unittest

from issueai.core import build_phase_envelope, workflow_registry


class WorkflowContractsTest(unittest.TestCase):
    def test_public_workflow_registry_has_four_named_workflows(self) -> None:
        registry = workflow_registry()
        self.assertEqual(
            set(registry),
            {"repository-recon", "repository-intent-review", "issue-hunt", "issue-probe"},
        )
        self.assertEqual(registry["repository-recon"].display_name, "Repository Recon")
        self.assertEqual(registry["repository-intent-review"].display_name, "Repository Intent Review")

    def test_phase_envelope_separates_static_and_dynamic_parts(self) -> None:
        first = build_phase_envelope(
            "repository-recon",
            "snapshot-and-entrypoints",
            {"entrypoints": ["app/main.py"], "repoRoot": "/tmp/repo", "reviewMode": "repository", "changedDomains": ["app"]},
        )
        second = build_phase_envelope(
            "repository-recon",
            "snapshot-and-entrypoints",
            {"changedDomains": ["app"], "reviewMode": "repository", "repoRoot": "/tmp/repo", "entrypoints": ["app/main.py"]},
        )
        self.assertEqual(first["cache"]["staticHash"], second["cache"]["staticHash"])
        self.assertEqual(first["cache"]["dynamicHash"], second["cache"]["dynamicHash"])
        self.assertIn("start from main", first["staticPrompt"].lower())
        self.assertEqual(first["dynamicPayload"]["repoRoot"], "/tmp/repo")
