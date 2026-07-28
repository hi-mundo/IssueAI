from pathlib import Path
import unittest

from issueai.core.repository_recon_graph import build_recon_findings, detect_redundancies
from issueai.core.repository_recon_profile import classify_path_roles


class ReconAnalysisTests(unittest.TestCase):
    def test_review_filename_does_not_become_controller_role(self) -> None:
        roles = classify_path_roles(Path("issueai/core/repository_intent_review.py"))
        self.assertNotIn("controllers", roles)

    def test_redundancy_ignores_test_only_fragmentation(self) -> None:
        redundancies = detect_redundancies(
            {
                "controllers": [
                    "issueai/core/repository_intent_review.py",
                    "tests/test_intent_review.py",
                ]
            }
        )
        self.assertEqual(redundancies, [])

    def test_recon_findings_ignore_conventional_entrypoint_name(self) -> None:
        findings = build_recon_findings(
            {
                "medianSourceLines": 40,
                "totalSourceFiles": 20,
                "dominantNamingStyle": "snake",
                "domainFileCounts": {"issueai": 12},
                "namingStyleCounts": {"snake": 12, "plain": 1},
                "largestFiles": [{"path": "issueai/cli.py", "lines": 280}],
            },
            [],
        )
        self.assertFalse(any(item["type"] == "naming-drift" for item in findings))

    def test_recon_findings_ignore_common_plain_module_names(self) -> None:
        findings = build_recon_findings(
            {
                "medianSourceLines": 40,
                "totalSourceFiles": 20,
                "dominantNamingStyle": "snake",
                "domainFileCounts": {"issueai": 12},
                "namingStyleCounts": {"snake": 12, "plain": 4},
                "largestFiles": [{"path": "issueai/core/workflows.py", "lines": 280}],
            },
            [],
        )
        self.assertFalse(any(item["type"] == "naming-drift" for item in findings))


if __name__ == "__main__":
    unittest.main()
