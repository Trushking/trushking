#!/usr/bin/env python3
"""
Универсальный поиск архетипов #WFS с авторазбивкой на части.
Запуск: python3 WFS_CORE/find_archetype.py <archetype_key>
Пример: python3 WFS_CORE/find_archetype.py fazan
"""

import os
import sys
from datetime import datetime

# ─── СЛОВАРИ КЛЮЧЕВЫХ СЛОВ ПО АРХЕТИПАМ ───
ARCHETYPES = {
    "tufyak": ["Тюфяк", "паралич воли", "апатия", "инерция", "бездействие",
               "пассивность", "аморфность", "бесформенность", "обездвиженность",
               "Passive Collapse"],
    "kisel":  ["Кисель", "тамас", "ложное смирение", "духовная лень",
               "безволие", "всё воля Бога", "я грешный", "не суетитесь",
               "смирись и терпи", "маскировка под благость"],
    "straus": ["Страус", "аноним", "анонимность", "голова в песок",
               "отрицание реальности", "уход от ответственности",
               "капитуляция"],
    "fazan":  ["Фазан", "оправдание", "декоратор ошибок", "имитация",
               "красивые объяснения", "отвлекающие манёвры"],
    "skvoznyak": ["Сквозняк", "паранойя", "ложные угрозы",
                  "теория заговора", "блокировка воли", "паника"],
    "zanuda": ["Зануда", "псевдо-интеллектуал", "бесконечный анализ",
               "информационный шум", "паралич анализа", "согласования"],
    "malyavka": ["Малявка", "суета", "имитация активности",
                 "мелкие ошибки", "отсутствие результата"],
    "krot":   ["Крот", "системный рецидивист", "повтор ошибок", "догматизм",
               "ригидность", "так всегда было"],
    "sova":   ["Сова", "фрагментация внимания", "уход в детали",
               "потеря формы", "потеря цели", "энергоспад"],
    "skryaga": ["Скряга", "воровство", "обесценивание", "занижение метрик",
                "скупость", "забывание благодарности"],
    "zuka":   ["Зука", "уязвлённое самолюбие", "обида", "месть",
               "желание доказать", "холодное молчание"],
    "kulak":  ["Кулак", "грубая сила", "примитивный редуктор",
               "физическое действие", "насилие"],
    "baklazhan": ["Баклажан", "доминация", "давление", "ультиматум",
                  "игнорирование обратной связи", "авторитет силы"],
    "bratishka": ["Братишка", "панибратство", "фамильярность",
                  "разрушение иерархии", "коррупция", "ложное равенство"],
    "avanturist": ["Авантюрист", "ложные обещания", "манипуляции",
                   "иллюзия исключительности", "риск ради дофамина",
                   "аферист", "подделки"],
    "fraer":  ["Фраер", "агент хаоса", "иррациональные данные",
               "сбой системы", "распад личности"],
}

# ─── ПАПКИ ДЛЯ ПОИСКА ───
SEARCH_DIRS = [
    "WFS_CORE/",
]

OUTPUT_BASE = "WFS_CORE/КНИГИ/##АРХЕТИПЫ_СВОЙСТВА"
CHUNK_SIZE = 500  # записей на один файл


def find_quotes(archetype_key):
    if archetype_key not in ARCHETYPES:
        print(f"Ошибка: архетип '{archetype_key}' не найден.")
        print(f"Доступные: {', '.join(ARCHETYPES.keys())}")
        return

    keywords = ARCHETYPES[archetype_key]
    results = []
    file_count = 0
    seen_quotes = set()  # для отсечения дублей

    for search_dir in SEARCH_DIRS:
        if not os.path.exists(search_dir):
            continue
        for root, dirs, files in os.walk(search_dir):
            for fname in files:
                if not fname.endswith(('.md', '.txt')):
                    continue
                fpath = os.path.join(root, fname)
                file_count += 1
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                        lines = f.readlines()
                except Exception:
                    continue

                for i, line in enumerate(lines):
                    for kw in keywords:
                        if kw.lower() in line.lower():
                            start = max(0, i - 4)
                            end = min(len(lines), i + 5)
                            context = ''.join(lines[start:end]).strip()
                            # отсечение дублей по нормализованному тексту
                            norm = context[:200].lower()
                            if norm in seen_quotes:
                                break
                            seen_quotes.add(norm)
                            results.append({
                                'file': fpath,
                                'line': i + 1,
                                'keyword': kw,
                                'quote': context,
                            })
                            break

    # ─── СОЗДАНИЕ ПАПКИ АРХЕТИПА ───
    folder_name = archetype_key.upper()
    out_dir = os.path.join(OUTPUT_BASE, folder_name)
    os.makedirs(out_dir, exist_ok=True)

    # ─── РАЗБИВКА НА ЧАСТИ ───
    if not results:
        single_file = os.path.join(out_dir, f"{folder_name}_001.md")
        with open(single_file, 'w', encoding='utf-8') as f:
            f.write(f"# RAW DATA: {folder_name}\n")
            f.write(f"**Дата:** {datetime.now().isoformat()}\n")
            f.write(f"**Найдено:** 0 совпадений\n\n")
            f.write("NO DATA\n")
        print(f"Нет данных. Создан пустой файл: {single_file}")
        return

    total_parts = (len(results) + CHUNK_SIZE - 1) // CHUNK_SIZE

    for part_idx in range(total_parts):
        start = part_idx * CHUNK_SIZE
        end = start + CHUNK_SIZE
        chunk = results[start:end]

        part_num = f"{part_idx + 1:03d}"
        part_file = os.path.join(out_dir, f"{folder_name}_{part_num}.md")

        with open(part_file, 'w', encoding='utf-8') as f:
            f.write(f"# RAW DATA: {folder_name}\n")
            f.write(f"**Дата:** {datetime.now().isoformat()}\n")
            f.write(f"**Часть:** {part_num} из {total_parts:03d}\n")
            f.write(f"**Записей в части:** {len(chunk)}\n")
            f.write(f"**Всего записей:** {len(results)}\n")
            f.write(f"**Проверено файлов:** {file_count}\n\n")

            for r in chunk:
                f.write(f"---\n")
                f.write(f"**[FILE]:** `{r['file']}`\n")
                f.write(f"**[LINE]:** {r['line']}\n")
                f.write(f"**[KEYWORD]:** {r['keyword']}\n")
                f.write(f"**[QUOTE]:**\n```\n{r['quote']}\n```\n\n")

    print(f"Готово.")
    print(f"Папка: {out_dir}/")
    print(f"Частей: {total_parts}")
    print(f"Всего записей: {len(results)} (проверено файлов: {file_count})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python3 WFS_CORE/find_archetype.py <archetype>")
        print(f"Доступные: {', '.join(ARCHETYPES.keys())}")
    else:
        find_quotes(sys.argv[1].lower())
