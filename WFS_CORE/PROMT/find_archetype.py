#!/usr/bin/env python3
"""
Универсальный поиск архетипов #WFS со сбором ПОЛНОЙ #СС (верхней и нижней).
Добавлена жёсткая привязка: блок #СС, а не одна строка.
Извлечение метрик из текста цитаты.
Запуск: python3 WFS_CORE/find_archetype.py <архетип>
"""
import os
import sys
import re
from datetime import datetime

ARCHETYPES = {
    "tufyak": ["Тюфяк", "паралич воли", "апатия", "инерция", "бездействие", "пассивность", "аморфность", "бесформенность", "обездвиженность", "Passive Collapse"],
    "kisel": ["Кисель", "тамас", "ложное смирение", "духовная лень", "безволие", "всё воля Бога", "я грешный", "не суетитесь", "смирись и терпи", "маскировка под благость"],
    "straus": ["Страус", "аноним", "анонимность", "голова в песок", "отрицание реальности", "уход от ответственности", "капитуляция"],
    "fazan": ["Фазан", "оправдание", "декоратор ошибок", "имитация", "красивые объяснения", "отвлекающие манёвры"],
    "skvoznyak": ["Сквозняк", "паранойя", "ложные угрозы", "теория заговора", "блокировка воли", "паника"],
    "zanuda": ["Зануда", "псевдо-интеллектуал", "бесконечный анализ", "информационный шум", "паралич анализа", "согласования"],
    "malyavka": ["Малявка", "суета", "имитация активности", "мелкие ошибки", "отсутствие результата"],
    "krot": ["Крот", "системный рецидивист", "повтор ошибок", "догматизм", "ригидность", "так всегда было"],
    "sova": ["Сова", "фрагментация внимания", "уход в детали", "потеря формы", "потеря цели", "энергоспад"],
    "skryaga": ["Скряга", "воровство", "обесценивание", "занижение метрик", "скупость", "забывание благодарности"],
    "zuka": ["Зука", "уязвлённое самолюбие", "обида", "месть", "желание доказать", "холодное молчание"],
    "kulak": ["Кулак", "грубая сила", "примитивный редуктор", "физическое действие", "насилие"],
    "baklazhan": ["Баклажан", "доминация", "давление", "ультиматум", "игнорирование обратной связи", "авторитет силы"],
    "bratishka": ["Братишка", "панибратство", "фамильярность", "разрушение иерархии", "коррупция", "ложное равенство"],
    "avanturist": ["Авантюрист", "ложные обещания", "манипуляции", "иллюзия исключительности", "риск ради дофамина", "аферист", "подделки"],
    "fraer": ["Фраер", "агент хаоса", "иррациональные данные", "сбой системы", "распад личности"],
}

SEARCH_DIRS = ["WFS_CORE"]
OUTPUT_BASE = "WFS_CORE/КНИГИ/##АРХЕТИПЫ_СВОЙСТВА"
CHUNK_SIZE = 100
MAX_SS_DIST = 50  # строк для поиска #СС

# ─── РЕГУЛЯРКИ ───
SS_FIELD = re.compile(r'\[([^:\]]+):\s*([^\]]+)\]')
METRIC_PATTERN = re.compile(r'(#[А-ЯA-Z_]+)\s*[=:]\s*([^,\s]+)')


def extract_all_fields(ss_text):
    """Извлекает ВСЕ поля из текста #СС (может быть многострочным)."""
    fields = {}
    if not ss_text:
        return fields
    for m in SS_FIELD.finditer(ss_text):
        key = m.group(1).strip()
        value = m.group(2).strip()
        fields[key] = value
    return fields


def find_ss_block(lines, idx, direction=-1, max_dist=MAX_SS_DIST):
    """
    Ищет блок #СС (несколько строк, начиная с [ИМЯ: ...]) в заданном направлении.
    direction = -1: вверх (до цитаты)
    direction = 1: вниз (после цитаты)
    Возвращает объединённую строку блока или None.
    """
    if direction == -1:
        rng = range(idx, max(-1, idx - max_dist), -1)
    else:
        rng = range(idx, min(len(lines), idx + max_dist))

    for i in rng:
        if '[ИМЯ:' in lines[i]:
            block_lines = []
            j = i
            while j < len(lines) and j < i + 15:
                line = lines[j].strip()
                if not line:
                    break
                # Строка похожа на часть #СС, если содержит поля в квадратных скобках
                if re.search(r'\[[^\]]+:\s*[^\]]+\]', line):
                    block_lines.append(line)
                    j += 1
                else:
                    break
            if block_lines:
                return ' '.join(block_lines)
    return None


def extract_metrics_from_text(text):
    """Извлекает метрики из текста цитаты (если они есть внутри)."""
    metrics = {}
    if not text:
        return metrics
    for m in METRIC_PATTERN.finditer(text):
        key = m.group(1)
        value = m.group(2).strip()
        if key not in metrics:
            metrics[key] = value
    return metrics


def find_quotes(archetype_key):
    if archetype_key not in ARCHETYPES:
        print(f"Ошибка: архетип '{archetype_key}' не найден.")
        print(f"Доступные: {', '.join(ARCHETYPES.keys())}")
        return

    keywords = ARCHETYPES[archetype_key]
    results = []
    file_count = 0
    seen_quotes = set()

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
                            norm = context[:200].lower()
                            if norm in seen_quotes:
                                break
                            seen_quotes.add(norm)

                            ss_top = find_ss_block(lines, i, direction=-1)
                            ss_bottom = find_ss_block(lines, i, direction=1)
                            metrics_from_quote = extract_metrics_from_text(context)

                            # Объединяем поля из верхней и нижней #СС
                            fields_top = extract_all_fields(ss_top)
                            fields_bottom = extract_all_fields(ss_bottom)

                            results.append({
                                'file': fpath,
                                'line': i + 1,
                                'keyword': kw,
                                'quote': context,
                                'ss_top': ss_top,
                                'ss_bottom': ss_bottom,
                                'fields_top': fields_top,
                                'fields_bottom': fields_bottom,
                                'metrics_from_quote': metrics_from_quote,
                            })
                            break

    folder_name = archetype_key.upper()
    out_dir = os.path.join(OUTPUT_BASE, folder_name)
    os.makedirs(out_dir, exist_ok=True)

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
            f.write(f"**Дата генерации:** {datetime.now().isoformat()}\n")
            f.write(f"**Часть:** {part_num} из {total_parts:03d}\n")
            f.write(f"**Записей в части:** {len(chunk)}\n")
            f.write(f"**Всего записей:** {len(results)}\n")
            f.write(f"**Проверено файлов:** {file_count}\n\n")

            for r in chunk:
                f.write(f"---\n")
                f.write(f"**[FILE]:** `{r['file']}`\n")
                f.write(f"**[LINE]:** {r['line']}\n")
                f.write(f"**[KEYWORD]:** {r['keyword']}\n")

                if r['ss_top']:
                    f.write(f"**[SS_TOP]:** `{r['ss_top']}`\n")
                    for k, v in r['fields_top'].items():
                        f.write(f"  - **{k}:** {v}\n")
                else:
                    f.write(f"**[SS_TOP]:** N/A\n")

                if r['ss_bottom']:
                    f.write(f"**[SS_BOTTOM]:** `{r['ss_bottom']}`\n")
                    for k, v in r['fields_bottom'].items():
                        f.write(f"  - **{k}:** {v}\n")
                else:
                    f.write(f"**[SS_BOTTOM]:** N/A\n")

                if r['metrics_from_quote']:
                    f.write(f"**[METRICS_FROM_QUOTE]:** {r['metrics_from_quote']}\n")

                f.write(f"**[QUOTE]:**\n```\n{r['quote']}\n```\n\n")

    print(f"Готово.")
    print(f"Папка: {out_dir}/")
    print(f"Частей: {total_parts}")
    print(f"Всего записей: {len(results)} (проверено файлов: {file_count})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python3 WFS_CORE/find_archetype.py <архетип>")
        print(f"Доступные: {', '.join(ARCHETYPES.keys())}")
    else:
        find_quotes(sys.argv[1].lower())
