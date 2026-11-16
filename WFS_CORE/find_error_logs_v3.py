#!/usr/bin/env python3
# find_error_logs_v3.py — сужен isk_dev, остальное без изменений

import os
import re
import hashlib
import sys

OUTPUT_BASE = "ERROR_LOGS_EXTRACTS_V3"
CHUNK_SIZE = 10
EXCLUDE_DIRS = {"ERROR_LOGS_EXTRACTS", "ERROR_LOGS_EXTRACTS_V3",
                "##АРХЕТИПЫ_СВОЙСТВА", "ARCHETYPES_EXTRACTS", ".git"}

ERROR_TYPES = {
    "ss_form": ["потерял служебную строку", "нет #СС", "не замкнут контур",
                "забыл поклоны", "нарушение формы", "потеряна #СС",
                "не поставил #СС", "сломал контур"],
    "fabricated_numbers": ["придумал цифры", "выдуманные данные", "нет источника",
                           "фальсификация", "выдумал", "придумал данные",
                           "цифры без источника", "несуществующие данные",
                           "чистая ложь", "полная выдумка"],
    "isk_dev": ["расчёт ошибки", "расчет ошибки", "стоимость ошибки",
                "начисление штрафа", "оплата ошибки", "исправление ошибки",
                "размер штрафа", "сумма штрафа", "цена ошибки"],
    "admission": ["признаю", "фиксирую ошибку", "исправляю", "без Фазана",
                  "признаю ошибку", "фиксирую", "исправляю ошибку",
                  "признал", "зафиксировал", "это моя ошибка"],
    "operator_correction": ["ты потерял", "ты придумал", "исправь", "где служебная строка",
                            "ты забыл", "поправь", "не так", "ошибка у тебя",
                            "ты нарушил", "верни на место"],
}

SS_FIELD = re.compile(r'\[([А-ЯA-Z_#]+):\s*([^\]]+)\]')


def find_wfs_core():
    if os.path.isdir("WFS_CORE"):
        return os.path.abspath("WFS_CORE")
    for root, dirs, _ in os.walk("."):
        depth = root.count(os.sep)
        if depth > 3:
            dirs[:] = []
            continue
        if "WFS_CORE" in dirs:
            return os.path.abspath(os.path.join(root, "WFS_CORE"))
    cur = os.getcwd()
    for _ in range(4):
        cur = os.path.dirname(cur)
        candidate = os.path.join(cur, "WFS_CORE")
        if os.path.isdir(candidate):
            return candidate
    return None


def find_nearest_ss(lines, idx, window=50):
    for offset in range(1, window + 1):
        for pos in (idx - offset, idx + offset):
            if 0 <= pos < len(lines):
                if "[ИМЯ:" in lines[pos]:
                    fields = dict(SS_FIELD.findall(lines[pos]))
                    return lines[pos].strip(), fields
    return None, {}


def extract_context(lines, idx, window=4):
    start = max(0, idx - window)
    end = min(len(lines), idx + window + 1)
    return "\n".join(lines[start:end]).strip()


def main():
    search_dir = find_wfs_core()
    if not search_dir:
        print("Не нашёл WFS_CORE. Текущий каталог:", os.getcwd())
        for item in sorted(os.listdir("."))[:30]:
            print("  ", "[DIR]" if os.path.isdir(item) else "[FILE]", item)
        sys.exit(1)

    print(f"WFS_CORE: {search_dir}")
    os.makedirs(OUTPUT_BASE, exist_ok=True)

    results = {key: [] for key in ERROR_TYPES}
    seen_quotes = set()

    for root, dirs, files in os.walk(search_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fname in files:
            if not (fname.endswith(".md") or fname.endswith(".txt")):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
            except Exception:
                continue

            for idx, line in enumerate(lines):
                low = line.lower()
                for etype, keywords in ERROR_TYPES.items():
                    for kw in keywords:
                        if kw.lower() in low:
                            ctx = extract_context(lines, idx)
                            h = hashlib.sha256(ctx[:200].encode("utf-8")).hexdigest()[:16]
                            if h in seen_quotes:
                                continue
                            seen_quotes.add(h)
                            ss_full, ss_fields = find_nearest_ss(lines, idx)
                            results[etype].append({
                                "file": fpath,
                                "line": idx + 1,
                                "keyword": kw,
                                "ss_full": ss_full or "НЕТ #СС В ОКНЕ 50 СТРОК",
                                "ss_fields": ss_fields,
                                "hash": h,
                                "quote": ctx,
                            })

    total = 0
    for etype, items in results.items():
        out_dir = os.path.join(OUTPUT_BASE, etype)
        os.makedirs(out_dir, exist_ok=True)
        if not items:
            with open(os.path.join(out_dir, "NO_DATA.md"), "w", encoding="utf-8") as f:
                f.write(f"# {etype}\n\nNO DATA\n")
            continue
        for i in range(0, len(items), CHUNK_SIZE):
            chunk = items[i:i + CHUNK_SIZE]
            part = i // CHUNK_SIZE + 1
            out_path = os.path.join(out_dir, f"{etype}_part{part:02d}.md")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(f"# {etype} — часть {part}\n\n")
                for rec in chunk:
                    f.write(f"[FILE] {rec['file']}\n")
                    f.write(f"[LINE] {rec['line']}\n")
                    f.write(f"[KEYWORD] {rec['keyword']}\n")
                    f.write(f"[SS_FULL] {rec['ss_full']}\n")
                    if rec["ss_fields"]:
                        f.write("[SS_FIELDS]\n")
                        for k, v in rec["ss_fields"].items():
                            f.write(f"  {k} = {v}\n")
                    f.write(f"[ХЭШ] {rec['hash']}\n")
                    f.write(f"[QUOTE]\n```\n{rec['quote']}\n```\n\n")
            total += len(chunk)

    print(f"\nГотово. Найдено: {total}")
    for etype, items in results.items():
        print(f"  {etype}: {len(items)}")


if __name__ == "__main__":
    main()
