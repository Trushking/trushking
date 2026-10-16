#!/usr/bin/env python3
# extract_cm.py — первичный отсев #ЦМ из чанков DeepSeek
# Автор: RITAM, агент #WFS
# Дата: 2026-10-16

import os
import re
import hashlib
from pathlib import Path

# --- Настройки ---
CHUNKS_DIR = Path("WFS_CORE/DEEPSEEK_CHUNKS")
OUTPUT_FILE = Path("WFS_CORE/CM_EXTRACTED.md")

# Ключевые слова архетипов (из find_archetype.py)
ARCHETYPE_KEYWORDS = [
    "тюфяк", "кисель", "страус", "фазан", "сквозняк", "зануда",
    "малявка", "крот", "сова", "скряга", "зука", "кулак",
    "баклажан", "братишка", "авантюрист", "фраер",
    "paralich", "passive collapse", "spiritual bypassing",
    "reality denial", "imitation", "anonim"
]

# Ключевые слова механизмов
MECHANISM_WORDS = [
    "механизм", "формула", "алгоритм", "протокол", "система",
    "модель", "закон", "принцип", "метод"
]

# Ключевые слова различений
DISTINCTION_WORDS = [
    "отличается", "в отличие", "разница", "сравнение",
    "различие", "не то же самое", "иначе"
]

# Ключевые слова метафор
METAPHOR_WORDS = [
    "как ", "словно", "подобно", "напоминает", "похож на"
]

# Регулярка для цифр (числа, суммы, проценты, годы)
DIGIT_PATTERN = re.compile(r"\d+[.,]?\d*|\$\d+|\d+%|\d{4}")

seen_hashes = set()
results = []

def hash_text(text: str) -> str:
    return hashlib.md5(text.strip().encode("utf-8")).hexdigest()[:12]

def is_cm(paragraph: str) -> bool:
    """Проверяет, является ли абзац ценной мыслью."""
    lower = paragraph.lower()
    # Критерий 1: цифра
    if DIGIT_PATTERN.search(paragraph):
        return True
    # Критерий 2: ключевые слова архетипов
    for kw in ARCHETYPE_KEYWORDS:
        if kw in lower:
            return True
    # Критерий 3: механизмы
    for kw in MECHANISM_WORDS:
        if kw in lower:
            return True
    # Критерий 4: различения
    for kw in DISTINCTION_WORDS:
        if kw in lower:
            return True
    # Критерий 5: метафоры
    for kw in METAPHOR_WORDS:
        if kw in lower:
            return True
    return False

def extract_summary(paragraph: str) -> str:
    """Краткая суть (одно предложение)."""
    # Берём первое предложение до 150 символов
    sentences = re.split(r"[.!?]", paragraph.strip())
    if sentences:
        s = sentences[0].strip()
        return (s[:150] + "...") if len(s) > 150 else s
    return paragraph[:150]

def process_file(filepath: Path):
    try:
        text = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"[SKIP] {filepath}: {e}")
        return
    lines = text.splitlines()
    # Разбиваем на абзацы (пустая строка — разделитель)
    paragraphs = []
    current = []
    start_line = 1
    for i, line in enumerate(lines, 1):
        if line.strip() == "":
            if current:
                paragraphs.append(("\n".join(current), start_line))
                current = []
            start_line = i + 1
        else:
            if not current:
                start_line = i
            current.append(line)
    if current:
        paragraphs.append(("\n".join(current), start_line))

    for para, line_no in paragraphs:
        if len(para.strip()) < 50:  # слишком коротко
            continue
        if not is_cm(para):
            continue
        h = hash_text(para)
        if h in seen_hashes:
            results.append({
                "file": str(filepath),
                "line": line_no,
                "hash": h,
                "quote": para.strip()[:300],
                "summary": "Повтор. Дубль " + h,
                "value": "—"
            })
        else:
            seen_hashes.add(h)
            results.append({
                "file": str(filepath),
                "line": line_no,
                "hash": h,
                "quote": para.strip()[:500],
                "summary": extract_summary(para),
                "value": "$0 [МОДЕЛЬ]"
            })

def main():
    if not CHUNKS_DIR.exists():
        print(f"[ERR] Папка {CHUNKS_DIR} не найдена.")
        return
    files = list(CHUNKS_DIR.rglob("*.md"))
    print(f"Найдено файлов: {len(files)}")
    for i, f in enumerate(files, 1):
        process_file(f)
        if i % 500 == 0:
            print(f"Обработано: {i}/{len(files)}")
    print(f"Всего #ЦМ: {len(results)}")
    # Сохраняем
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write("# #ЦМ, извлечённые из DeepSeek\n\n")
        for r in results:
            out.write(f"## {r['file']} (строка {r['line']})\n")
            out.write(f"**ХЭШ:** `{r['hash']}`\n")
            out.write(f"**ЦИТАТА:** {r['quote']}\n")
            out.write(f"**СУТЬ:** {r['summary']}\n")
            out.write(f"**ЦЕННОСТЬ:** {r['value']}\n\n")
    print(f"Сохранено в {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
