#!/usr/bin/env python3
"""Validate and summarize a small paired pilot using only the Python standard library."""

from __future__ import annotations

import argparse
import csv
import math
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


FIELDS = (
    "run_id",
    "task_id",
    "paired_task_id",
    "condition",
    "started_at",
    "agent",
    "model",
    "model_version",
    "protocol_version",
    "task_type",
    "max_turns",
    "turns",
    "clarification_questions",
    "operator_corrections",
    "unsupported_claims",
    "accepted",
    "blind_quality_1_5",
    "elapsed_seconds",
    "operator_IH",
    "operator_SEI",
    "operator_FI",
    "notes",
)
REQUIRED_TEXT = (
    "run_id",
    "task_id",
    "condition",
    "started_at",
    "agent",
    "model",
    "model_version",
    "protocol_version",
    "task_type",
)
REQUIRED_COUNTS = (
    "max_turns",
    "turns",
    "clarification_questions",
    "operator_corrections",
    "unsupported_claims",
)
OPERATOR_SCALES = ("operator_IH", "operator_SEI", "operator_FI")


@dataclass(frozen=True)
class Run:
    row_number: int
    values: dict[str, str]
    started_at: datetime
    accepted: bool
    quality: int | None
    turns: int

    @property
    def assessed(self) -> bool:
        return self.quality is not None

    @property
    def successful(self) -> bool:
        return self.accepted and self.quality is not None and self.quality >= 4


def _parse_nonnegative_int(value: str, field: str, row_number: int) -> int:
    try:
        result = int(value)
    except ValueError as exc:
        raise ValueError(f"строка {row_number}: {field} должно быть целым числом") from exc
    if result < 0:
        raise ValueError(f"строка {row_number}: {field} не может быть отрицательным")
    return result


def _parse_optional_scale(value: str, field: str, row_number: int) -> int | None:
    if not value:
        return None
    result = _parse_nonnegative_int(value, field, row_number)
    if result > 10:
        raise ValueError(f"строка {row_number}: {field} должно быть от 0 до 10")
    return result


def _parse_timestamp(value: str, row_number: int) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(
            f"строка {row_number}: started_at должно быть датой ISO 8601 "
            "(например, 2026-10-05T12:30:00Z)"
        ) from exc


def load_runs(path: Path) -> list[Run]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames is None:
                raise ValueError("CSV-файл пуст или в нём отсутствует строка заголовков")
            missing_fields = [field for field in FIELDS if field not in reader.fieldnames]
            if missing_fields:
                raise ValueError(f"в CSV отсутствуют столбцы: {', '.join(missing_fields)}")

            runs: list[Run] = []
            seen_run_ids: set[str] = set()
            for row_number, row in enumerate(reader, start=2):
                if None in row:
                    raise ValueError(f"строка {row_number}: число значений не совпадает с заголовком")
                values = {key: (value or "").strip() for key, value in row.items() if key}
                if not any(values.values()):
                    continue

                for field in REQUIRED_TEXT:
                    if not values.get(field):
                        raise ValueError(f"строка {row_number}: не заполнено обязательное поле {field}")
                if values["condition"] not in {"baseline", "wfs"}:
                    raise ValueError(f"строка {row_number}: condition должно быть baseline или wfs")
                if values["run_id"] in seen_run_ids:
                    raise ValueError(f"строка {row_number}: run_id повторяется ({values['run_id']})")
                seen_run_ids.add(values["run_id"])

                counts = {
                    field: _parse_nonnegative_int(values[field], field, row_number)
                    for field in REQUIRED_COUNTS
                }
                if counts["max_turns"] == 0:
                    raise ValueError(f"строка {row_number}: max_turns должно быть больше нуля")
                if counts["turns"] > counts["max_turns"]:
                    raise ValueError(f"строка {row_number}: turns не может превышать max_turns")

                if values["accepted"] not in {"yes", "no"}:
                    raise ValueError(f"строка {row_number}: accepted должно быть yes или no")
                quality_value = values.get("blind_quality_1_5", "")
                quality = None
                if quality_value:
                    quality = _parse_nonnegative_int(quality_value, "blind_quality_1_5", row_number)
                    if not 1 <= quality <= 5:
                        raise ValueError(f"строка {row_number}: blind_quality_1_5 должно быть от 1 до 5")

                elapsed = values.get("elapsed_seconds", "")
                if elapsed:
                    try:
                        elapsed_value = float(elapsed)
                    except ValueError as exc:
                        raise ValueError(
                            f"строка {row_number}: elapsed_seconds должно быть числом"
                        ) from exc
                    if not math.isfinite(elapsed_value) or elapsed_value < 0:
                        raise ValueError(
                            f"строка {row_number}: elapsed_seconds должно быть конечным "
                            "неотрицательным числом"
                        )

                for field in OPERATOR_SCALES:
                    _parse_optional_scale(values.get(field, ""), field, row_number)

                runs.append(
                    Run(
                        row_number=row_number,
                        values=values,
                        started_at=_parse_timestamp(values["started_at"], row_number),
                        accepted=values["accepted"] == "yes",
                        quality=quality,
                        turns=counts["turns"],
                    )
                )
    except OSError as exc:
        raise ValueError(f"не удалось прочитать {path}: {exc}") from exc
    except csv.Error as exc:
        raise ValueError(f"ошибка CSV в {path}: {exc}") from exc
    return runs


def initialize(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"файл уже существует, он не перезаписан: {path}")
    if not path.parent.is_dir():
        raise FileNotFoundError(f"папка не существует: {path.parent}")
    try:
        with path.open("x", encoding="utf-8", newline="") as target:
            writer = csv.writer(target)
            writer.writerow(FIELDS)
    except OSError as exc:
        raise ValueError(f"не удалось создать {path}: {exc}") from exc
    print(f"Создан пустой журнал: {path}")


def _success_summary(runs: Iterable[Run]) -> tuple[int, int, int]:
    selected = list(runs)
    assessed = [run for run in selected if run.assessed]
    successful = sum(run.successful for run in assessed)
    return len(selected), len(assessed), successful


def _rate(successful: int, assessed: int) -> str:
    return "нет данных" if assessed == 0 else f"{successful / assessed:.1%}"


def report(runs: list[Run]) -> None:
    if not runs:
        print("В журнале пока нет запусков.")
        return

    by_condition: dict[str, list[Run]] = defaultdict(list)
    for run in runs:
        by_condition[run.values["condition"]].append(run)

    print("Сводка по условию")
    print("Успех = accepted=yes и слепая оценка качества >= 4/5.")
    for condition in ("baseline", "wfs"):
        selected = by_condition.get(condition, [])
        total, assessed, successful = _success_summary(selected)
        successful_runs = [run for run in selected if run.successful]
        median_turns = (
            f"{statistics.median(run.turns for run in successful_runs):g}"
            if successful_runs
            else "нет данных"
        )
        print(
            f"- {condition}: запусков {total}; оценено {assessed}; "
            f"успехов {successful}; доля успеха {_rate(successful, assessed)}; "
            f"медиана ходов среди успешных {median_turns}"
        )

    by_week: dict[tuple[str, str], list[Run]] = defaultdict(list)
    for run in runs:
        iso = run.started_at.isocalendar()
        week = f"{iso.year}-W{iso.week:02d}"
        by_week[(week, run.values["condition"])].append(run)

    print("\nДинамика по ISO-неделям")
    print("Неделя | Условие | Запусков | Оценено | Успешно | Доля успеха")
    for (week, condition), selected in sorted(by_week.items()):
        total, assessed, successful = _success_summary(selected)
        print(
            f"{week} | {condition} | {total} | {assessed} | {successful} | "
            f"{_rate(successful, assessed)}"
        )

    pairs: dict[str, dict[str, list[Run]]] = defaultdict(lambda: defaultdict(list))
    for run in runs:
        pair_id = run.values.get("paired_task_id", "")
        if pair_id:
            pairs[pair_id][run.values["condition"]].append(run)

    candidate_pairs = [
        (pair_id, conditions)
        for pair_id, conditions in pairs.items()
        if len(conditions.get("baseline", [])) == 1 and len(conditions.get("wfs", [])) == 1
    ]
    complete_pairs = [
        pair_id
        for pair_id, conditions in candidate_pairs
        if conditions["baseline"][0].values["task_id"] == conditions["wfs"][0].values["task_id"]
    ]
    inconsistent_pairs = len(candidate_pairs) - len(complete_pairs)
    assessed_pairs = [
        pair_id
        for pair_id in complete_pairs
        if pairs[pair_id]["baseline"][0].assessed and pairs[pair_id]["wfs"][0].assessed
    ]
    successful_both = [
        pair_id
        for pair_id in assessed_pairs
        if pairs[pair_id]["baseline"][0].successful and pairs[pair_id]["wfs"][0].successful
    ]
    paired_turn_diffs = [
        pairs[pair_id]["wfs"][0].turns - pairs[pair_id]["baseline"][0].turns
        for pair_id in successful_both
    ]
    print("\nПарное сравнение")
    print(
        f"- полных пар (ровно один запуск каждого условия): {len(complete_pairs)}; "
        f"оценено в обоих условиях: {len(assessed_pairs)}; "
        f"пар с разными task_id исключено: {inconsistent_pairs}"
    )
    if paired_turn_diffs:
        print(
            "- медиана разницы ходов WFS - baseline среди пар, успешных в обоих условиях: "
            f"{statistics.median(paired_turn_diffs):g}"
        )
    else:
        print("- разница ходов среди пар, успешных в обоих условиях: нет данных")
    print("Эти описательные сводки не устанавливают причинность и не заменяют проверку исходных ответов.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    init_parser = subparsers.add_parser("init", help="создать пустой CSV-журнал")
    init_parser.add_argument("csv_path", type=Path)
    report_parser = subparsers.add_parser("report", help="проверить CSV и вывести сводку")
    report_parser.add_argument("csv_path", type=Path)
    args = parser.parse_args()

    try:
        if args.command == "init":
            initialize(args.csv_path)
        else:
            report(load_runs(args.csv_path))
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
