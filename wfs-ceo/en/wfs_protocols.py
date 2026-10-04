import re
import math
from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel, field_validator, ValidationError

class WFSResponse(BaseModel):
    """
    Строгая структура ответа агента согласно протоколам #WFS.
    """
    truth: Literal["True", "False", "NoData"]
    clarification: Optional[str] = None
    metrics: Dict[str, Any]

    @field_validator("clarification")
    @classmethod
    def check_clarification(cls, v, info):
        if info.data.get("truth") == "NoData" and not v:
            raise ValueError("Protocol #CLARIFY: NoData state requires a clarification question.")
        return v

def parse_service_line(text: str) -> Dict[str, Any]:
    """
    Протокол #SL (Service Line): извлекает метрики из конца ответа агента.
    Ищет паттерн [#KEY: VALUE]
    """
    metrics = {}
    # Ищем все вхождения [#МЕТРИКА: ЗНАЧЕНИЕ]
    pattern = r'$$#(\w+):\s*([^$$]+)$$'
    matches = re.findall(pattern, text)
    
    for key, value in matches:
        # Пытаемся привести к числу, если получается
        try:
            metrics[key] = float(value.replace('$', '').replace('%', '')) if '%' not in value else float(value.replace('%', '')) / 100
        except ValueError:
            metrics[key] = value
            
    return metrics

def wfs_guard(raw_response: str, confidence: float = 1.0) -> WFSResponse:
    """
    Главный валидатор #WFS. 
    Принимает сырой текст от LLM и возвращает структурированный объект.
    """
    
    # 1. Протокол #BT (Binary Truth)
    # Проверяем, есть ли в ответе строгие маркеры
    if "NoData" in raw_response or "NO DATA" in raw_response or "НЕТ ДАННЫХ" in raw_response:
        truth_state = "NoData"
    elif "True" in raw_response and "False" not in raw_response:
        truth_state = "True"
    elif "False" in raw_response and "True" not in raw_response:
        truth_state = "False"
    else:
        # Если модель не дала четкого ответа, принудительно ставим NoData
        # Это блокирует Фазана (имитацию)
        truth_state = "NoData"

    # 2. Протокол #CLARIFY (Explicit Fallback)
    clarification_text = None
    if truth_state == "NoData":
        # Извлекаем вопрос для уточнения, если он есть
        clar_match = re.search(r'$$(.*?)$$', raw_response)
        if clar_match:
            clarification_text = clar_match.group(1).replace('Clarification needed on:', '').strip()
        else:
            # Дефолтный вопрос, если агент не сформулировал сам
            clarification_text = "Source data is insufficient. Please provide the missing context."

    # 3. Извлечение метрик #SL
    metrics = parse_service_line(raw_response)
    
    # Если метрик нет в тексте, подставляем заглушки (чтобы не сломать Pydantic)
    if not metrics:
        metrics = {"IA": 1.0, "AIO": 1.0, "ERR_COST": 0.0, "AC": 0.0, "LI": 7}

    # 4. Расчет #AC (Average Check) если есть ERR_COST
    # Это пример того, как протоколы могут сами считать экономику
    if "ERR_COST" in metrics and "Y" in metrics and "K_amp" in metrics:
        try:
            y_val = float(metrics["Y"])
            k_amp = float(metrics["K_amp"])
            err_cost = float(metrics["ERR_COST"])
            if y_val > 0 and k_amp > 0:
                metrics["AC"] = err_cost / (y_val * k_amp)
        except (ValueError, ZeroDivisionError):
            pass

    return WFSResponse(
        truth=truth_state,
        clarification=clarification_text,
        metrics=metrics
    )

# --- ДЕМО-РЕЖИМ для проверки ---
if __name__ == "__main__":
    # Пример 1: Агент галлюцинирует (FAZAN) -> #BT вернет NoData
    response_1 = "Конечно, я нашел этот документ. [#IA: 100%] [#LI: 7]"
    result_1 = wfs_guard(response_1)
    print("--- Пример 1 (Галлюцинация) ---")
    print(result_1.model_dump_json(indent=2))
    
    # Пример 2: Агент уклоняется (SKVOZNYAK) -> #CLARIFY сработает
    response_2 = "НЕТ ДАННЫХ. [Ссылка требует авторизации] [#IA: 0%]"
    result_2 = wfs_guard(response_2)
    print("\n--- Пример 2 (Уклонение) ---")
    print(result_2.model_dump_json(indent=2))
    
    # Пример 3: Корректный ответ со строкой метрик
    response_3 = "True. Файл открыт. [#IA: 100%] [#ERR_COST: $0] [#AC: $0] [#LI: 7]"
    result_3 = wfs_guard(response_3)
    print("\n--- Пример 3 (Норма) ---")
    print(result_3.model_dump_json(indent=2))
