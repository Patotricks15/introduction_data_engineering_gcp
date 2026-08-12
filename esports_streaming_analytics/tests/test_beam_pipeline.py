import unittest
from types import SimpleNamespace

from src.beam_pipeline import profile_from_bigtable_row


class BeamPipelineTest(unittest.TestCase):
    def test_extracts_latest_profile_cells_from_bigtable_row(self) -> None:
        row = SimpleNamespace(
            cells={
                "profile": {
                    b"display_name": [SimpleNamespace(value=b"Nova")],
                    b"team": [SimpleNamespace(value=b"Solaris")],
                    b"region": [SimpleNamespace(value=b"BR")],
                    b"rank": [SimpleNamespace(value=b"Diamond")],
                }
            }
        )

        profile = profile_from_bigtable_row(row)

        self.assertEqual(profile["display_name"], "Nova")
        self.assertEqual(profile["team"], "Solaris")
        self.assertEqual(profile["region"], "BR")
        self.assertEqual(profile["rank"], "Diamond")

    def test_missing_bigtable_profile_uses_explicit_unknown_values(self) -> None:
        self.assertEqual(
            profile_from_bigtable_row(None),
            {"display_name": "unknown", "team": "unknown", "region": "unknown", "rank": "unknown"},
        )


if __name__ == "__main__":
    unittest.main()