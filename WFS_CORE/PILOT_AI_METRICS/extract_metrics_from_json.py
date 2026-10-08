import json
import re
import pandas as pd

def extract_ss(line):
    # Ищем только русские названия метрик
    pattern = r'$$#(ИА|ИАОП|СЧ|ФАКТ_ОШИБКИ|ФИ|ИЗ|ИХ|ИНФ)\s*:\s*(.*?)$$'
    matches = re.findall(pattern, line)
    
    metrics = {}
    for key, value in matches:
        if '%' in value or '$' in value:
            try:
                # Пытаемся превратить проценты и доллары в числа
                numeric_value = float(value.strip('%$'))
                unit = '%' if '%' in value else '$'
            except ValueError:
                continue  # Пропускаем, если не получилось
        else:
            numeric_value = value
            unit = ''
        
        metrics[key.upper()] = {
            'value': numeric_value,
            'unit': unit
        }
    
    return metrics

def process_file(file_path):
    data = []
    
    with open(file_path, encoding='utf-8') as f:
        # Этот цикл работает даже с огромными файлами!
        for line_number, raw_line in enumerate(f, start=1):
            # Пробуем прочитать строку как JSON
            try:
                obj = json.loads(raw_line)
                message = obj.get('text', '') or obj.get('content', '')
            except Exception:
                # Возможно, это просто текстовое сообщение
                message = raw_line.strip()
            
            # Ищем служебную строку в сообщении
            ss_start = message.find('[#')
            if ss_start != -1:
                # Берём всю часть до конца сообщения
                ss_part = message[ss_start:]
                
                # Извлекаем метрики
                metrics = extract_ss(ss_part)
                if metrics:
                    # Добавляем данные в наш список
                    record = {'line_number': line_number}
                    for metric_name, details in metrics.items():
                        record[f'{metric_name}_VALUE'] = details['value']
                        record[f'{metric_name}_UNIT'] = details['unit']
                    
                    # Сохраняем само сообщение для контекста
                    record['MESSAGE'] = message[:500] + '...'  # Только начало
                    data.append(record)
    
    df = pd.DataFrame(data)
    return df

if __name__ == "__main__":
    input_file = 'deepseek_logs.json'  # Замените на имя вашего файла
    output_csv = 'metrics_deepseek_pilot.csv'
    
    print("Начинаю обработку...")
    df = process_file(input_file)
    print(f"Найдено {len(df)} записей с метриками.")
    
    # Разделим результат на части, чтобы обойти лимит GitHub
    chunk_size = 100000  # Примерно 20-25 МБ
    chunks = [df[i:i+chunk_size] for i in range(0, len(df), chunk_size)]
    
    for idx, chunk in enumerate(chunks):
        filename = f'metrics_chunk_{idx}.csv'
        chunk.to_csv(filename, index=False)
        print(f"Сохранена часть {filename} ({len(chunk)} строк)")
