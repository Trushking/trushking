#!/usr/bin/env python3
"""Read #WFS metric tags from Markdown without changing the source archive."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from datetime import date
from pathlib import Path


OUTPUT_FIELDS = (
    "source_file",
    "source_line",
    "agent_raw",
    "date_raw",
    "date_iso_day",
    "session_raw",
    "message_raw",
    "context_complete",
    "source_line_sha256",
    "metric",
    "value_raw",
    "numeric_value",
    "unit",
    "possible_exact_repeat",
    "repeat_index",
    "exact_line_copies_in_source",
)
METRIC_TAG = re.compile(r"\[#(?P<key>[\w-]+):\s*(?P<value>[^\]]*)\]")
CONTEXT_TAG = re.compile(
    r"\[(?P<key>ИМЯ|ДАТА|СЕСС|СООБЩ):\s*(?P<value>[^\]]*)\]"
)
NUMBER = re.compile(r"^[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?$")
DATE_PREFIX = re.compile(r"^\s*(\d{4}-\d{2}-\d{2})")


@dataclass(frozen=True)
class MetricRecord:
    source_file: str
    source_line: int
    fingerprint: str
    repeat_index: int
    agent_raw: str
    date_raw: str
    date_iso_day: str
    session_raw: str
    message_raw: str
    context_complete: str
    metric: str
    value_raw: str
    numeric_value: str
    unit: str


def _metadata(line: str) -> dict[str, str]:
    return {
        match.group("key"): match.group("value").strip()
        for match in CONTEXT_TAG.finditer(line)
    }


def _iso_day(date_raw: str) -> str:
    match = DATE_PREFIX.match(date_raw)
    if not match:
        return ""
    candidate = match.group(1)
    try:
        return date.fromisoformat(candidate).isoformat()
    except ValueError:
        return ""


def _numeric_value(raw: str) -> tuple[str, str]:
    value = raw.strip()
    currency = value.startswith("$")
    percent = value.endswith("%")
    candidate = value.removeprefix("$").removesuffix("%").strip()
    if not NUMBER.fullmatch(candidate):
        return "", ""
    try:
        number = Decimal(candidate.replace(",", ""))
    except InvalidOperation:
        return "", ""
    unit = "currency_symbol_$" if currency else "percent" if percent else "unit_unspecified"
    return format(number.normalize(), "f"), unit


def scan_archive(
    source_dir: Path,
) -> tuple[list[MetricRecord], Counter[tuple[str, str]]]:
    if not source_dir.is_dir():
        raise ValueError(f"папка архива не найдена: {source_dir}")

    records: list[MetricRecord] = []
    seen_lines: Counter[tuple[str, str]] = Counter()
    try:
        files = sorted(
            (path for path in source_dir.rglob("*") if path.is_file() and path.suffix.lower() == ".md"),
            key=lambda path: path.as_posix(),
        )
        for path in files:
            relative_path = path.relative_to(source_dir).as_posix()
            try:
                lines = path.read_text(encoding="utf-8-sig").splitlines()
            except (OSError, UnicodeError) as exc:
                raise ValueError(f"не удалось прочитать {path}: {exc}") from exc

            for line_number, line in enumerate(lines, start=1):
                matches = list(METRIC_TAG.finditer(line))
                if not matches:
                    continue
                metadata = _metadata(line)
                fingerprint = hashlib.sha256(line.strip().encode("utf-8")).hexdigest()
                line_key = (relative_path, fingerprint)
                seen_lines[line_key] += 1
                repeat_index = seen_lines[line_key]
                context = {
                    "agent_raw": metadata.get("ИМЯ", ""),
                    "date_raw": metadata.get("ДАТА", ""),
                    "session_raw": metadata.get("СЕСС", ""),
                    "message_raw": metadata.get("СООБЩ", ""),
                }
                complete = all(context.values())
                for match in matches:
                    value_raw = match.group("value").strip()
                    numeric_value, unit = _numeric_value(value_raw)
                    records.append(
                        MetricRecord(
                            source_file=relative_path,
                            source_line=line_number,
                            fingerprint=fingerprint,
                            repeat_index=repeat_index,
                            agent_raw=context["agent_raw"],
                            date_raw=context["date_raw"],
                            date_iso_day=_iso_day(context["date_raw"]),
                            session_raw=context["session_raw"],
                            message_raw=context["message_raw"],
                            context_complete="yes" if complete else "no",
                            metric=f"#{match.group('key')}",
                            value_raw=value_raw,
                            numeric_value=numeric_value,
                            unit=unit,
                        )
                    )
    except OSError as exc:
        raise ValueError(f"не удалось просмотреть {source_dir}: {exc}") from exc

    copies_by_line: Counter[tuple[str, str]] = Counter()
    for record in records:
        copies_by_line[(record.source_file, record.fingerprint)] = max(
            copies_by_line[(record.source_file, record.fingerprint)],
            record.repeat_index,
        )

    records.sort(key=lambda record: (record.source_file, record.source_line))
    return records, copies_by_line


def extract_archive(source_dir: Path, output_csv: Path) -> None:
    if output_csv.exists():
        raise FileExistsError(f"файл уже существует, он не перезаписан: {output_csv}")
    if not output_csv.parent.is_dir():
        raise FileNotFoundError(f"папка результата не существует: {output_csv.parent}")

    records, copies_by_line = scan_archive(source_dir)
    try:
        with output_csv.open("x", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=OUTPUT_FIELDS)
            writer.writeheader()
            for record in records:
                copies = copies_by_line[(record.source_file, record.fingerprint)]
                writer.writerow(
                    {
                        "source_file": record.source_file,
                        "source_line": record.source_line,
                        "agent_raw": record.agent_raw,
                        "date_raw": record.date_raw,
                        "date_iso_day": record.date_iso_day,
                        "session_raw": record.session_raw,
                        "message_raw": record.message_raw,
                        "context_complete": record.context_complete,
                        "source_line_sha256": record.fingerprint,
                        "metric": record.metric,
                        "value_raw": record.value_raw,
                        "numeric_value": record.numeric_value,
                        "unit": record.unit,
                        "possible_exact_repeat": "yes" if copies > 1 else "no",
                        "repeat_index": record.repeat_index,
                        "exact_line_copies_in_source": copies,
                    }
                )
    except OSError as exc:
        raise ValueError(f"не удалось записать {output_csv}: {exc}") from exc
    print(f"Извлечено записей метрик: {len(records)}")
    print(f"Файл-указатель на исходные строки: {output_csv}")
    print("Исходные Markdown-файлы не изменялись; повторные строки сохранены и помечены.")


def timeline(csv_path: Path) -> None:
    groups: dict[tuple[str, str, str, str], list[Decimal]] = {}
    seen_source_lines: set[tuple[str, str, str, str]] = set()
    dated_numeric_rows = 0
    excluded_exact_repeats = 0
    excluded_unusable = 0

    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames is None or any(field not in reader.fieldnames for field in OUTPUT_FIELDS):
                raise ValueError("CSV не содержит заголовки, созданные командой extract")
            for row_number, row in enumerate(reader, start=2):
                date_value = (row.get("date_iso_day") or "").strip()
                numeric_value = (row.get("numeric_value") or "").strip()
                if not date_value or not numeric_value:
                    excluded_unusable += 1
                    continue
                dated_numeric_rows += 1

                source_file = row.get("source_file") or ""
                fingerprint = row.get("source_line_sha256") or ""
                metric = row.get("metric") or ""
                value_raw = row.get("value_raw") or ""
                repeat_key = (source_file, fingerprint, metric, value_raw)
                if (row.get("repeat_index") or "") != "1":
                    excluded_exact_repeats += 1
                    continue
                if repeat_key in seen_source_lines:
                    excluded_exact_repeats += 1
                    continue
                seen_source_lines.add(repeat_key)

                try:
                    value = Decimal(numeric_value)
                except InvalidOperation as exc:
                    raise ValueError(
                        f"строка {row_number}: некорректное numeric_value {numeric_value!r}"
                    ) from exc
                agent = (row.get("agent_raw") or "").strip() or "UNKNOWN"
                unit = (row.get("unit") or "").strip() or "unit_unspecified"
                group_key = (metric, unit, date_value[:7], agent)
                groups.setdefault(group_key, []).append(value)
    except OSError as exc:
        raise ValueError(f"не удалось прочитать {csv_path}: {exc}") from exc
    except csv.Error as exc:
        raise ValueError(f"ошибка CSV в {csv_path}: {exc}") from exc

    print("Динамика явно записанных числовых значений (описательно, не оценка эффективности)")
    print("Метрика | Единица из записи | Месяц | Агент из строки | n | Медиана | Мин. | Макс.")
    for (metric, unit, month, agent), values in sorted(groups.items()):
        print(
            f"{metric} | {unit} | {month} | {agent} | {len(values)} | "
            f"{statistics.median(values)} | {min(values)} | {max(values)}"
        )
    print(
        f"\nСтрок с датой и числом до очистки точных повторов: {dated_numeric_rows}; "
        f"исключено точных повторов: {excluded_exact_repeats}; "
        f"без даты или однозначного числа: {excluded_unusable}."
    )
    print(
        "Повторы остаются в исходном CSV. Значение UNKNOWN означает, что имя агента "
        "отсутствовало в той же строке; имя не выводилось из пути файла."
    )


def inventory(csv_path: Path) -> None:
    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames is None or any(field not in reader.fieldnames for field in OUTPUT_FIELDS):
                raise ValueError("CSV не содержит заголовки, созданные командой extract")
            counts: dict[str, Counter[str]] = {}
            source_files: dict[str, set[str]] = {}
            for row_number, row in enumerate(reader, start=2):
                metric = (row.get("metric") or "").strip()
                if not metric:
                    raise ValueError(f"строка {row_number}: пустое имя метрики")
                if metric not in counts:
                    counts[metric] = Counter()
                    source_files[metric] = set()
                summary = counts[metric]
                summary["occurrences"] += 1
                summary["dated"] += bool(row.get("date_iso_day"))
                summary["complete_context"] += row.get("context_complete") == "yes"
                summary["numeric"] += bool(row.get("numeric_value"))
                summary["possible_repeat"] += row.get("possible_exact_repeat") == "yes"
                source_files[metric].add(row.get("source_file") or "")
    except OSError as exc:
        raise ValueError(f"не удалось прочитать {csv_path}: {exc}") from exc
    except csv.Error as exc:
        raise ValueError(f"ошибка CSV в {csv_path}: {exc}") from exc

    print("Инвентаризация исходных отметок (это не оценка эффективности)")
    print("Метрика | Строк | Файлов | Есть дата | Полный контекст | Число распознано | Повторы-кандидаты")
    for metric in sorted(counts):
        summary = counts[metric]
        print(
            f"{metric} | {summary['occurrences']} | {len(source_files[metric])} | "
            f"{summary['dated']} | {summary['complete_context']} | {summary['numeric']} | "
            f"{summary['possible_repeat']}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    extract_parser = subparsers.add_parser("extract", help="создать CSV-указатель на метрики в Markdown")
    extract_parser.add_argument("source_dir", type=Path)
    extract_parser.add_argument("output_csv", type=Path)
    inventory_parser = subparsers.add_parser("inventory", help="сосчитать покрытие извлечённого CSV")
    inventory_parser.add_argument("csv_path", type=Path)
    timeline_parser = subparsers.add_parser(
        "timeline",
        help="показать помесячную сводку явных чисел без точных повторов строк",
    )
    timeline_parser.add_argument("csv_path", type=Path)
    args = parser.parse_args()

    try:
        if args.command == "extract":
            extract_archive(args.source_dir, args.output_csv)
        elif args.command == "inventory":
            inventory(args.csv_path)
        else:
            timeline(args.csv_path)
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
