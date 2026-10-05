import pandas as pd

# Загружаем ваши CSV-метрики
df = pd.read_csv('agent_metrics.csv')  # Укажите имя вашего файла

# Простой анализ
print("Среднее время ответа:", df['Response Time'].mean())
print("Процент ошибок:", df['Error Rate'].mean() * 100)
print("Стоимость ошибки (#AC):", df['Cost of Error'].sum())

# Связь с ICM
# Если у вас есть столбцы, соответствующие вашей формуле #LI или #AC, добавьте их сюда
# Например:
# print("Индекс звена (#LI):", df['Link Index'].mean())
