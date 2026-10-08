import csv
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from archive_extract import OUTPUT_FIELDS, extract_archive, scan_archive, timeline


class ArchiveExtractTests(unittest.TestCase):
    def test_extracts_metric_and_context_without_editing_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "archive"
            root.mkdir()
            source = root / "agent.md"
            line = (
                "[ИМЯ: TEST] [ДАТА: 2026-10-05 XX:YY] [СЕСС: PILOT] "
                "[СООБЩ: 4/10] [#ИА: 95%] [#ИСК_DEV: $1,200]"
            )
            source.write_text(f"{line}\n{line}\n", encoding="utf-8")

            records, copies = scan_archive(root)
            self.assertEqual([record.metric for record in records], ["#ИА", "#ИСК_DEV", "#ИА", "#ИСК_DEV"])
            self.assertEqual(records[0].numeric_value, "95")
            self.assertEqual(records[0].unit, "percent")
            self.assertEqual(records[1].numeric_value, "1200")
            self.assertEqual(records[1].unit, "currency_symbol_$")
            self.assertEqual(records[0].date_iso_day, "2026-10-05")
            self.assertEqual(records[0].context_complete, "yes")
            self.assertEqual(copies[(records[0].source_file, records[0].fingerprint)], 2)
            self.assertEqual(source.read_text(encoding="utf-8"), f"{line}\n{line}\n")

            output = root.parent / "metrics.csv"
            extract_archive(root, output)
            with output.open(encoding="utf-8", newline="") as result:
                rows = list(csv.DictReader(result))
            self.assertEqual(rows[0]["possible_exact_repeat"], "yes")
            self.assertEqual(rows[0]["exact_line_copies_in_source"], "2")
            self.assertEqual(list(rows[0]), list(OUTPUT_FIELDS))
            self.assertEqual(rows[0]["source_line_sha256"], records[0].fingerprint)

            captured = StringIO()
            with redirect_stdout(captured):
                timeline(output)
            self.assertIn(
                "Строк с датой и числом до очистки точных повторов: 4",
                captured.getvalue(),
            )
            self.assertIn("исключено точных повторов: 2", captured.getvalue())

    def test_leaves_non_numeric_and_invalid_dates_uninterpreted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "agent.md").write_text(
                "[ДАТА: 2026-99-40] [#БЛАГОСЛ: признание фабрикации]\n",
                encoding="utf-8",
            )

            records, _ = scan_archive(root)
            self.assertEqual(records[0].date_iso_day, "")
            self.assertEqual(records[0].numeric_value, "")
            self.assertEqual(records[0].unit, "")
            self.assertEqual(records[0].value_raw, "признание фабрикации")


if __name__ == "__main__":
    unittest.main()
