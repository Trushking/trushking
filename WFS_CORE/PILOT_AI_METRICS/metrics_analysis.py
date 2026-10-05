import pandas as pd

# Загрузка вашего CSV-файла с данными пилота
# Замените имя файла на то, которое у вас есть в папке!
df = pd.read_csv('agent_metrics.csv')

# Базовый анализ
print("🔹 Количество сессий:", len(df))
print("🔸 Среднее время ответа агента:", df['Response Time'].mean())
print("🔸 Процент ошибок (#ERR_RATE):", df['Error Rate'].mean() * 100)
print("🔸 Средняя стоимость ошибки (#AC):", df['Cost of Error'].sum() / len(df))

# Связь с вашей формулой #LI (Link Index)
# Если у вас есть такой столбец в файле, раскомментируйте эту строку:
# print("🔸 Индекс звена (#LI):", df['Link Index'].mean())
