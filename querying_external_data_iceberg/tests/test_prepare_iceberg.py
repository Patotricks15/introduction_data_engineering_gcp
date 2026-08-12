import unittest

from src.prepare_iceberg import parse_tip_records


class ParseTipRecordsTest(unittest.TestCase):
    def test_parses_public_tips_csv_with_stable_ids_and_types(self) -> None:
        csv_text = (
            "total_bill,tip,sex,smoker,day,time,size\n"
            "16.99,1.01,Female,No,Sun,Dinner,2\n"
            "10.34,1.66,Male,No,Sun,Dinner,3\n"
        )

        records = parse_tip_records(csv_text)

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["tip_id"], 1)
        self.assertEqual(records[0]["total_bill"], 16.99)
        self.assertEqual(records[1]["party_size"], 3)
        self.assertIsInstance(records[1]["tip"], float)


if __name__ == "__main__":
    unittest.main()