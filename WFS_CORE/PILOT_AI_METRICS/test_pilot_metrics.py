import csv
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO

from pilot_metrics import FIELDS, initialize, load_runs, report


def row(run_id, task_id, condition, accepted="yes", quality="4", turns="3", pair="pair-1"):
    return {
        "run_id": run_id,
        "task_id": task_id,
        "paired_task_id": pair,
        "condition": condition,
        "started_at": "2026-10-05T12:30:00Z",
        "agent": "test-agent",
        "model": "test-model",
        "model_version": "test-version",
        "protocol_version": "wfs-1" if condition == "wfs" else "none",
        "task_type": "text",
        "max_turns": "10",
        "turns": turns,
        "clarification_questions": "0",
        "operator_corrections": "0",
        "unsupported_claims": "0",
        "accepted": accepted,
        "blind_quality_1_5": quality,
        "elapsed_seconds": "",
        "operator_IH": "",
        "operator_SEI": "",
        "operator_FI": "",
        "notes": "",
    }


class PilotMetricsTests(unittest.TestCase):
    def test_initialize_writes_template_and_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pilot.csv"
            initialize(path)
            with path.open(encoding="utf-8", newline="") as source:
                self.assertEqual(next(csv.reader(source)), list(FIELDS))
            with self.assertRaises(FileExistsError):
                initialize(path)

    def test_report_keeps_missing_quality_out_of_denominator(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pilot.csv"
            with path.open("w", encoding="utf-8", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerow(row("1", "task-1", "baseline", quality=""))
                writer.writerow(row("2", "task-1", "wfs", quality="5", turns="2"))

            runs = load_runs(path)
            output = StringIO()
            with redirect_stdout(output):
                report(runs)
            summary = output.getvalue()
            self.assertIn("baseline: запусков 1; оценено 0; успехов 0; доля успеха нет данных", summary)
            self.assertIn("wfs: запусков 1; оценено 1; успехов 1; доля успеха 100.0%", summary)
            self.assertIn("оценено в обоих условиях: 0", summary)

    def test_invalid_turn_count_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pilot.csv"
            with path.open("w", encoding="utf-8", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerow(row("1", "task-1", "baseline", turns="11"))

            with self.assertRaisesRegex(ValueError, "turns не может превышать max_turns"):
                load_runs(path)

    def test_pair_with_different_task_ids_is_not_compared(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pilot.csv"
            with path.open("w", encoding="utf-8", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerow(row("1", "task-1", "baseline"))
                writer.writerow(row("2", "task-2", "wfs"))

            output = StringIO()
            with redirect_stdout(output):
                report(load_runs(path))
            self.assertIn("полных пар (ровно один запуск каждого условия): 0", output.getvalue())
            self.assertIn("пар с разными task_id исключено: 1", output.getvalue())


if __name__ == "__main__":
    unittest.main()
