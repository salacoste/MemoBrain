# MemoBrain Documentation

## Обзор документации

| Документ | Описание |
|----------|----------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Общая архитектура системы, диаграммы, design decisions |
| [DATA-MODEL.md](./DATA-MODEL.md) | Структуры данных: ReasoningNode, Edge, Notes, операции |
| [API-REFERENCE.md](./API-REFERENCE.md) | Полный справочник API с примерами |
| [USAGE-GUIDE.md](./USAGE-GUIDE.md) | Практическое руководство, паттерны, best practices |
| [TEMPORAL-KNOWLEDGE.md](./TEMPORAL-KNOWLEDGE.md) | Управление временными аспектами знаний |
| [API-TEMPORAL.md](./API-TEMPORAL.md) | **API для TemporalMemoBrain** (NEW) |

## Версии MemoBrain

| Класс | Файл | SDK | Temporal |
|-------|------|-----|----------|
| `MemoBrain` | `memobrain.py` | OpenAI | ❌ |
| `MemoBrainAnthropic` | `memobrain_anthropic.py` | Anthropic | ❌ |
| **`TemporalMemoBrain`** | `memobrain_temporal.py` | Anthropic | ✅ |

**Рекомендуется:** `TemporalMemoBrain` для долгосрочного использования

---

## Быстрый старт

```python
import asyncio
from memobrain_anthropic import MemoBrainAnthropic

async def main():
    # Инициализация с z.ai
    memory = MemoBrainAnthropic(
        api_key="your_key",
        base_url="https://api.z.ai/api/anthropic",
        model_name="GLM-4.5-Air"
    )

    # Создать задачу
    memory.init_memory("Исследовать архитектуру NestJS")

    # Сохранить эпизод рассуждения
    await memory.memorize([
        {"role": "assistant", "content": "Ищу паттерны..."},
        {"role": "user", "content": "Найдено: модульная архитектура"}
    ])

    # Посмотреть граф
    print(memory.graph.pretty_print())

asyncio.run(main())
```

---

## Структура проекта

```
memobrain/
├── src/
│   ├── memobrain.py           # OpenAI SDK версия
│   ├── memobrain_anthropic.py # Anthropic SDK (z.ai)
│   ├── problem_tree.py        # ReasoningGraph
│   ├── schema.py              # Pydantic модели
│   └── prompts.py             # Системные промпты
├── docs/                      # ← Вы здесь
│   ├── README.md
│   ├── ARCHITECTURE.md
│   ├── DATA-MODEL.md
│   ├── API-REFERENCE.md
│   ├── USAGE-GUIDE.md
│   └── TEMPORAL-KNOWLEDGE.md
├── examples/
│   └── ...
├── .venv/                     # Virtual environment
└── test_*.py                  # Тесты
```

---

## Ключевые концепции

### ReasoningGraph

Направленный граф, где:
- **Узлы** = шаги рассуждения (task, subtask, evidence, summary)
- **Рёбра** = связи (decompose, refine, support)

### Episode

Единица памяти = пара сообщений:
```python
[
    {"role": "assistant", "content": "Мысль агента"},
    {"role": "user", "content": "Ответ инструмента"}
]
```

### Операции

| Операция | Описание |
|----------|----------|
| `init_memory()` | Создать корневой task |
| `memorize()` | Сохранить эпизод (LLM генерирует патч) |
| `recall()` | Оптимизировать память (flush/fold) |
| `save_memory()` | Сохранить в JSON |
| `load_memory()` | Загрузить из JSON |

---

## Конфигурация z.ai

```python
API_KEY = "your_zai_api_key"
BASE_URL = "https://api.z.ai/api/anthropic"

# Доступные модели
MODELS = {
    "fast": "GLM-4.5-Air",   # Быстрая, дешевая
    "best": "GLM-4.7"        # Лучшее качество
}
```

---

## Запуск тестов

```bash
cd memobrain
source .venv/bin/activate

# Базовый тест
python test_memobrain_anthropic.py

# Комплексный сценарий
python test_complex_scenario.py
```

---

## Известные ограничения

1. **LLM зависимость**: Требуются вызовы LLM для memorize/recall
2. **JSON парсинг**: LLM должна выдавать валидный JSON
3. **Однопоточность**: Не thread-safe
4. **Нет timestamps**: Оригинальная версия не хранит время создания узлов

---

## Дальнейшее чтение

- [arXiv Paper](https://arxiv.org/abs/2601.08079) - Оригинальная научная статья
- [GitHub](https://github.com/qhjqhj00/MemoBrain) - Исходный репозиторий
- [HuggingFace Models](https://huggingface.co/TommyChien) - Предобученные модели
