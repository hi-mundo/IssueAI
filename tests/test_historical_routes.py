from __future__ import annotations

import unittest

from issueai.core import NormalizedRepositoryContract, NormalizedSourceFileContract, canonicalize, choose_scopes


class HistoricalRoutesTests(unittest.TestCase):
    def test_canonicalize_maps_legacy_aliases(self) -> None:
        self.assertEqual(canonicalize("state"), "state_reuse")
        self.assertEqual(canonicalize("typing"), "contract")
        self.assertEqual(canonicalize("boundary"), "boundary")

    def test_choose_scopes_stays_deep_for_small_repositories(self) -> None:
        normalized: NormalizedRepositoryContract = {
            "files": [
                {"path": "src/app.py", "kind": "source", "vendor": False, "generated": False},
                {"path": "src/service.py", "kind": "source", "vendor": False, "generated": False},
            ]
        }

        mode, scopes, count = choose_scopes(normalized)

        self.assertEqual(mode, "deep")
        self.assertEqual(scopes, [])
        self.assertEqual(count, 2)

    def test_choose_scopes_picks_dominant_roots_for_large_repositories(self) -> None:
        files: list[NormalizedSourceFileContract] = []
        for index in range(1800):
            files.append({"path": f"src/module_{index}.py", "kind": "source", "vendor": False, "generated": False})
        for index in range(500):
            files.append({"path": f"lib/part_{index}.py", "kind": "source", "vendor": False, "generated": False})
        for index in range(40):
            files.append({"path": f"tests/test_{index}.py", "kind": "source", "vendor": False, "generated": False})
        normalized: NormalizedRepositoryContract = {"files": files}

        mode, scopes, count = choose_scopes(normalized)

        self.assertEqual(mode, "normal")
        self.assertEqual(scopes[:2], ["src", "lib"])
        self.assertEqual(count, 2340)


if __name__ == "__main__":
    unittest.main()
