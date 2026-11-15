#!/usr/bin/env python3
# find_error_logs.py
# Поиск логов ошибок в корпусе знаний #WFS
# Адаптация find_archetype.py под логи ошибок

import os
import re
import hashlib

SEARCH_DIR = "WFS_CORE"
OUTPUT_BASE = "ERROR_LOGS_EXTRACTS"
CHUNK_SIZE = 10

EXCLUDE_DIRS = {"ERROR_LOGS_EXTRACTS", "##АРХЕТИПЫ_СВОЙСТВА", "ARCHETYPES_EXTRACTS"}

ERROR_TYPES = {
    "ss_form": [
        "потерял служебную строку", "нет #СС", "не замкнут контур",
        "забыл поклоны", "нарушение формы", "потеряна #СС",
        "не поставил #СС", "сломал контур"
    ],
    "fabricated_numbers": [
        "придумал цифры", "выдуманные данные", "нет источника",
        "фальсификация", "выдумал", "придумал данные",
        "цифры без источника", "несуществующие данные"
    ],
    "isk_dev": [
        "#ИСК_DEV", "расчёт ошибки", "штраф", "исправление ошибки",
        "стоимость ошибки", "начисление штрафа", "оплата ошибки"
    ],
    "admission": [
        "признаю", "фиксирую ошибку", "исправляю", "без Фазана",
        "признаю ошибку", "фиксирую", "исправляю ошибку",
        "признал", "зафиксировал"
    ],
    "operator_correction": [
        "ты потерял", "ты придумал", "исправь", "где служебная строка",
        "ты забыл", "поправь", "не так", "ошибка у тебя",
        "ты нарушил", "верни на место"
    ],
}

SS_FIELD = re.compile(r'\[([А-ЯA-Z_#]+):\s*([^\]]+)\]')

def find_nearest_ss(lines, idx, window=50):
    """Ищет ближайшую служебную строку вверх или вниз от фрагмента."""
    for offset in range(1, window + 1):
        for pos in (idx - offset, idx + offset):
            if 0 <= pos < len(lines):
                if "[ИМЯ:" in lines[pos]:
                    fields = dict(SS_FIELD.findall(lines[pos]))
                    return lines[pos].strip(), fields
    return None, {}

def extract_context(lines, idx, window=4):
    """Берёт окно ±window строк вокруг найденного фрагмента."""
    start = max(0, idx - window)
    end = min(len(lines), idx + window + 1)
    return "\n".join(lines[start:end]).strip()

def main():
    if not os.path.isdir(SEARCH_DIR):
        print(f"Папка {SEARCH_DIR} не найдена.")
        return

    os.makedirs(OUTPUT_BASE, exist_ok=True)

    results = {key: [] for key in ERROR_TYPES}
    seen_quotes = set()

    for root, dirs, files in os.walk(SEARCH_DIR):
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
        if not items:
            out_path = os.path.join(OUTPUT_BASE, etype, "NO_DATA.md")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(f"# {etype}\n\nNO DATA\n")
            continue

        for i in range(0, len(items), CHUNK_SIZE):
            chunk = items[i:i + CHUNK_SIZE]
            part = i // CHUNK_SIZE + 1
            out_dir = os.path.join(OUTPUT_BASE, etype)
            os.makedirs(out_dir, exist_ok=True)
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

    print(f"Готово. Найдено фрагментов: {total}")
    print(f"Результаты в папке: {OUTPUT_BASE}")
    for etype, items in results.items():
        print(f"  {etype}: {len(items)}")

if __name__ == "__main__":
    main()
