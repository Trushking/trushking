#!/usr/bin/env python3
"""
Механический экстрактор абзацев с упоминанием архетипов #WFS.
НЕ использует DEV-ИИ. НЕ пропускает. Выводит ВСЁ.
Запуск: python3 WFS_CORE/PROMT/extract_archetype_paragraphs.py <архетип>
"""
import os
import sys
import re
from datetime import datetime

ARCHETYPES = {
    "tufyak": ["Тюфяк", "паралич воли", "апатия", "инерция", "бездействие", "пассивность"],
    "kisel": ["Кисель", "тамас", "ложное смирение", "духовная лень", "безволие", "я грешный"],
    "straus": ["Страус", "аноним", "анонимность", "голова в песок", "отрицание реальности"],
    "fazan": ["Фазан", "оправдание", "декоратор ошибок", "имитация"],
    "skvoznyak": ["Сквозняк", "паранойя", "ложные угрозы", "теория заговора", "паника"],
    "zanuda": ["Зануда", "псевдо-интеллектуал", "бесконечный анализ", "информационный шум"],
    "malyavka": ["Малявка", "суета", "имитация активности"],
    "krot": ["Крот", "системный рецидивист", "повтор ошибок", "догматизм"],
    "sova": ["Сова", "фрагментация внимания", "уход в детали", "потеря цели"],
    "skryaga": ["Скряга", "воровство", "обесценивание", "занижение метрик", "скупость"],
    "zuka": ["Зука", "уязвлённое самолюбие", "обида", "месть"],
    "kulak": ["Кулак", "грубая сила", "примитивный редуктор"],
    "baklazhan": ["Баклажан", "доминация", "давление", "ультиматум"],
    "bratishka": ["Братишка", "панибратство", "фамильярность", "разрушение иерархии"],
    "avanturist": ["Авантюрист", "ложные обещания", "манипуляции", "иллюзия исключительности"],
    "fraer": ["Фраер", "агент хаоса", "иррациональные данные"],
}

SEARCH_DIRS = ["WFS_CORE"]
OUTPUT_BASE = "WFS_CORE/ARCHETYPES_EXTRACTS"
EXCLUDE_DIRS = ["##АРХЕТИПЫ_СВОЙСТВА", "ARCHETYPES_EXTRACTS", "chunks", "chunks_100k", "TEMP"]

SS_PATTERN = re.compile(r'\[ИМЯ:\s*[^\]]+\]')


def is_excluded(path):
    norm = path.replace('\\', '/')
    return any(d in norm for d in EXCLUDE_DIRS)


def find_ss(lines, idx, direction=-1, max_dist=100):
    if direction == -1:
        rng = range(idx - 1, max(-1, idx - max_dist), -1)
    else:
        rng = range(idx + 1, min(len(lines), idx + max_dist))
    for i in rng:
        if '[ИМЯ:' in lines[i]:
            block = [lines[i].strip()]
            j = i + 1
            while j < len(lines) and j < i + 10:
                if re.search(r'\[[^\]]+:\s*[^\]]+\]', lines[j]):
                    block.append(lines[j].strip())
                    j += 1
                else:
                    break
            return ' '.join(block)
    return None


def extract_paragraph(lines, idx):
    """Извлекает ВЕСЬ абзац вокруг idx (до пустой строки или заголовка)."""
    # Ищем начало абзаца вверх
    start = idx
    while start > 0 and lines[start - 1].strip() and not lines[start - 1].strip().startswith('#'):
        start -= 1
    # Ищем конец абзаца вниз
    end = idx
    while end < len(lines) - 1 and lines[end + 1].strip() and not lines[end + 1].strip().startswith('#'):
        end += 1
    return ''.join(lines[start:end + 1]).strip()


def main(archetype_key):
    if archetype_key not in ARCHETYPES:
        print(f"Ошибка: '{archetype_key}' не найден.")
        print(f"Доступные: {', '.join(ARCHETYPES.keys())}")
        return

    keywords = [k.lower() for k in ARCHETYPES[archetype_key]]
    results = []
    seen = set()
    file_count = 0

    for search_dir in SEARCH_DIRS:
        if not os.path.exists(search_dir):
            continue
        for root, dirs, files in os.walk(search_dir):
            dirs[:] = [d for d in dirs if not is_excluded(os.path.join(root, d))]
            if is_excluded(root):
                continue
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
                    line_low = line.lower()
                    for kw in keywords:
                        if kw in line_low:
                            para = extract_paragraph(lines, i)
                            norm = para[:200].lower()
                            if norm in seen:
                                break
                            seen.add(norm)

                            ss_top = find_ss(lines, i, direction=-1)
                            ss_bottom = find_ss(lines, i, direction=1)

                            results.append({
                                'file': fpath,
                                'line': i + 1,
                                'keyword': kw,
                                'ss_top': ss_top,
                                'ss_bottom': ss_bottom,
                                'paragraph': para,
                            })
                            break

    out_dir = os.path.join(OUTPUT_BASE, archetype_key.upper())
    os.makedirs(out_dir, exist_ok=True)

    if not results:
        out_file = os.path.join(out_dir, f"{archetype_key.upper()}_001.md")
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(f"# RAW DATA: {archetype_key.upper()}\n")
            f.write(f"**Дата:** {datetime.now().isoformat()}\n")
            f.write(f"**Найдено:** 0\n\nNO DATA\n")
        print(f"Нет данных: {out_file}")
        return

    CHUNK = 10
    total_parts = (len(results) + CHUNK - 1) // CHUNK
    for part_idx in range(total_parts):
        chunk = results[part_idx * CHUNK:(part_idx + 1) * CHUNK]
        part_num = f"{part_idx + 1:03d}"
        out_file = os.path.join(out_dir, f"{archetype_key.upper()}_{part_num}.md")

        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(f"# RAW DATA: {archetype_key.upper()}\n")
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
                f.write(f"**[SS_TOP]:** `{r['ss_top'] or 'N/A'}`\n")
                f.write(f"**[SS_BOTTOM]:** `{r['ss_bottom'] or 'N/A'}`\n")
                f.write(f"**[PARAGRAPH]:**\n```\n{r['paragraph']}\n```\n\n")

    print(f"Готово. Папка: {out_dir}/")
    print(f"Частей: {total_parts}. Всего записей: {len(results)}. Проверено файлов: {file_count}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python3 WFS_CORE/PROMT/extract_archetype_paragraphs.py <архетип>")
        print(f"Доступные: {', '.join(ARCHETYPES.keys())}")
    else:
        main(sys.argv[1].lower())
