import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class IssueAIPluginManifestTests(unittest.TestCase):
    def test_host_plugin_manifests_exist(self) -> None:
        self.assertTrue((ROOT / ".codex-plugin" / "plugin.json").exists())
        self.assertTrue((ROOT / ".claude-plugin" / "plugin.json").exists())
        self.assertTrue((ROOT / ".cursor-plugin" / "plugin.json").exists())

    def test_host_plugin_manifests_share_same_identity(self) -> None:
        codex = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text())
        claude = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
        cursor = json.loads((ROOT / ".cursor-plugin" / "plugin.json").read_text())

        self.assertEqual(codex["name"], "issueai")
        self.assertEqual(codex["name"], claude["name"])
        self.assertEqual(codex["name"], cursor["name"])
        self.assertEqual(codex["interface"]["displayName"], "IssueAI")
        self.assertEqual(codex["interface"]["logo"], "./assets/plugin-logo.svg")
        self.assertEqual(codex["skills"], "./skills/")

    def test_logo_asset_exists(self) -> None:
        self.assertTrue((ROOT / "assets" / "logo.png").exists())
        self.assertTrue((ROOT / "assets" / "plugin-logo.svg").exists())

    def test_installed_skills_have_ui_metadata(self) -> None:
        expected = {
            "repository-recon": ("display_name: \"Repository Recon\"", "allow_implicit_invocation: true"),
            "repository-intent-review": ("display_name: \"Repository Intent Review\"", "allow_implicit_invocation: true"),
            "issue-hunt": ("display_name: \"Issue Hunt\"", "allow_implicit_invocation: true"),
            "issue-probe": ("display_name: \"Issue Probe\"", "allow_implicit_invocation: false"),
        }
        for skill, markers in expected.items():
            path = ROOT / "skills" / skill / "agents" / "openai.yaml"
            self.assertTrue(path.exists(), path.as_posix())
            content = path.read_text()
            for marker in markers:
                self.assertIn(marker, content)


if __name__ == "__main__":
    unittest.main()
