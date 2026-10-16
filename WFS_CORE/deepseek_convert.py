import json, os, hashlib, re
from datetime import datetime

INPUT = "deepseek_data-2026-10-17.json"   # путь к архиву
OUT_MD = "DEEPSEEK_MD"                     # папка для MD
OUT_CHUNKS = "DEEPSEEK_CHUNKS"             # папка для нарезанных блоков
CHUNK_SIZE = 10                             # блоков в одном файле

os.makedirs(OUT_MD, exist_ok=True)
os.makedirs(OUT_CHUNKS, exist_ok=True)

with open(INPUT, encoding='utf-8') as f:
    data = json.load(f)

print(f"Загружено чатов: {len(data)}")

def extract_messages(chat):
    """Извлекает все сообщения из mapping."""
    mapping = chat.get('mapping', {})
    nodes = []
    for node_id, node in mapping.items():
        msg = node.get('message')
        if not msg:
            continue
        for frag in msg.get('fragments', []):
            ftype = frag.get('type', '')
            content = frag.get('content', '')
            if content:
                nodes.append({
                    'node_id': node_id,
                    'type': ftype,
                    'content': content,
                    'time': msg.get('inserted_at', '')
                })
    return nodes

# --- ШАГ 1: СОХРАНЯЕМ КАЖДЫЙ ЧАТ КАК MD ---
all_blocks = []
for idx, chat in enumerate(data):
    title = chat.get('title', f'chat_{idx}')
    cid = chat.get('id', '')
    inserted = chat.get('inserted_at', '')
    
    safe_title = re.sub(r'[^\w\-]+', '_', title)[:50]
    md_file = os.path.join(OUT_MD, f"{idx:03d}_{safe_title}.md")
    
    messages = extract_messages(chat)
    
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(f"# ЧАТ: {title}\n")
        f.write(f"**ID:** {cid}\n")
        f.write(f"**Дата:** {inserted}\n")
        f.write(f"**Сообщений:** {len(messages)}\n\n---\n\n")
        
        for m in messages:
            f.write(f"**[{m['type']}]** ({m['time']})\n")
            f.write(f"{m['content']}\n\n---\n\n")
            all_blocks.append({
                'chat': title,
                'chat_id': cid,
                'type': m['type'],
                'content': m['content'],
                'time': m['time']
            })
    
    print(f"  [{idx+1}/{len(data)}] {md_file}: {len(messages)} сообщений")

print(f"\nВсего блоков: {len(all_blocks)}")

# --- ШАГ 2: РЕЖЕМ ПО CHUNK_SIZE С ХЭШАМИ ---
for part_idx in range(0, len(all_blocks), CHUNK_SIZE):
    chunk = all_blocks[part_idx:part_idx + CHUNK_SIZE]
    part_num = f"{part_idx // CHUNK_SIZE + 1:04d}"
    out_file = os.path.join(OUT_CHUNKS, f"DEEPSEEK_{part_num}.md")
    
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(f"# DEEPSEEK CHUNK {part_num}\n")
        f.write(f"**Дата генерации:** {datetime.now().isoformat()}\n")
        f.write(f"**Блоков в чанке:** {len(chunk)}\n\n---\n\n")
        
        for b in chunk:
            h = hashlib.sha256(b['content'].encode('utf-8')).hexdigest()[:16]
            f.write(f"**[CHAT]:** {b['chat']}\n")
            f.write(f"**[CHAT_ID]:** {b['chat_id']}\n")
            f.write(f"**[TYPE]:** {b['type']}\n")
            f.write(f"**[TIME]:** {b['time']}\n")
            f.write(f"**[ХЭШ]:** `{h}`\n")
            f.write(f"**[QUOTE]:**\n```\n{b['content']}\n```\n\n---\n\n")

print(f"Готово.")
print(f"MD-файлы: {OUT_MD}/")
print(f"Чанки: {OUT_CHUNKS}/ ({len(all_blocks)//CHUNK_SIZE + 1} файлов)")
