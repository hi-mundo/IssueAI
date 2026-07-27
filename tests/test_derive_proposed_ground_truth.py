from __future__ import annotations

import unittest

from evals.scripts.derive_proposed_ground_truth import canonicalize, score_case


class DeriveProposedGroundTruthTests(unittest.TestCase):
    def test_canonicalize_maps_typing_to_contract(self) -> None:
        self.assertEqual(canonicalize("typing"), "contract")
        self.assertEqual(canonicalize("state"), "state_reuse")

    def test_score_case_reads_real_prepared_artifacts(self) -> None:
        # Uses one prepared artifact directory already present in local benchmark state.
        from pathlib import Path

        artifact_dir = Path("/private/tmp/bug-hunt-unmapped-40-20260725/artifacts/aiohttp-3296")
        if not artifact_dir.exists():
            self.skipTest("prepared local artifact directory not available")
        route = score_case(artifact_dir)
        self.assertTrue(route)
        self.assertLessEqual(len(route), 3)


if __name__ == "__main__":
    unittest.main()
