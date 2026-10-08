import pandas as pd

# Замените имя файла на то, которое реально лежит рядом!
df = pd.read_csv('agent_metrics.csv')

# Проверка наличия нужных колонок
if 'Response Time' not in df.columns or 'Error Rate' not in df.columns or 'Cost of Error' not in df.columns:
    print("❗ Ошибка! Файл не содержит необходимых колонок.")
else:
    # Основные метрики
    sessions_count = len(df)
    avg_response_time = round(df['Response Time'].mean(), 2)  # Среднее время ответа
    error_rate_percent = round(df['Error Rate'].mean() * 100, 2)  # Процент ошибок
    total_cost_of_error = df['Cost of Error'].sum()
    
    # Средняя стоимость ошибки (#AC), если сессий больше нуля
    if sessions_count > 0:
        avg_cost_per_session = round(total_cost_of_error / sessions_count, 2)
    else:
        avg_cost_per_session = "N/A"

    # Форматированный вывод
    print(f"🔹 Количество сессий: {sessions_count}")
    print(f"🔸 Среднее время ответа агента: {avg_response_time} сек")
    print(f"🔸 Процент ошибок (#ERR_RATE): {error_rate_percent}%")
    print(f"🔸 Общая стоимость всех ошибок: ${total_cost_of_error:.2f}")
    print(f"🔸 Средняя стоимость ошибки на сессию (#AC): ${avg_cost_per_session}")
