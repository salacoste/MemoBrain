# Temporal MemoBrain API Reference

## TemporalMemoBrain

Расширенная версия MemoBrain с поддержкой timestamps, версионирования и multi-participant.

```python
from memobrain_temporal import TemporalMemoBrain
```

---

## Constructor

```python
memory = TemporalMemoBrain(
    api_key: str,           # API ключ
    base_url: str,          # URL API (z.ai: "https://api.z.ai/api/anthropic")
    model_name: str,        # Модель (GLM-4.5-Air, GLM-4.7)
    session_id: str = None, # ID сессии (auto-generated если не указан)
    default_participant: str = "agent"  # Участник по умолчанию
)
```

**Пример:**

```python
memory = TemporalMemoBrain(
    api_key="your_key",
    base_url="https://api.z.ai/api/anthropic",
    model_name="GLM-4.5-Air",
    session_id="sprint_1",
    default_participant="Architect",
)
```

---

## Core Methods

### `init_memory(task, tags=None)`

Инициализация памяти с задачей.

```python
memory.init_memory(
    task="Design authentication system",
    tags=["auth", "architecture"]
)
```

### `async memorize(new_messages, tags=None, participant=None)`

Сохранение эпизода с метаданными.

```python
await memory.memorize(
    new_messages=[
        {"role": "assistant", "content": "Implementing JWT..."},
        {"role": "user", "content": "Implementation complete"}
    ],
    tags=["auth", "implementation"],
    participant="Developer",
)
```

---

## Temporal Methods (NEW)

### `add_knowledge(content, kind, tags, participant, supersedes, link_to)`

Добавить знание напрямую (без LLM).

```python
node_id = memory.add_knowledge(
    content="JWT tokens selected for auth",
    kind="evidence",              # evidence, subtask, etc.
    tags=["auth", "decision"],
    participant="Architect",
    supersedes=None,              # Список ID узлов для замены
    link_to=1,                    # Связать с узлом (task)
)
```

**Возвращает:** `int` - ID нового узла

### `update_knowledge(old_node_id, new_content, participant)`

Обновить знание (создать superseding узел).

```python
new_id = memory.update_knowledge(
    old_node_id=2,
    new_content="Changed from sessions to JWT for scalability",
    participant="Architect",
)
# Node 2 теперь superseded by new_id
```

**Возвращает:** `int` - ID нового узла

### `get_current_knowledge(tag=None)`

Получить актуальные знания (без superseded).

```python
# Все актуальные
nodes = memory.get_current_knowledge()

# По тегу
auth_nodes = memory.get_current_knowledge(tag="auth")
```

**Возвращает:** `List[TemporalReasoningNode]`

### `get_knowledge_history(tag)`

Полная история по тегу (включая superseded).

```python
history = memory.get_knowledge_history(tag="auth")
for node in history:
    status = "current" if not node.is_superseded() else f"→{node.superseded_by}"
    print(f"[{node.created_at}] {status}: {node.thought}")
```

### `get_latest(tag)`

Самое свежее знание по тегу.

```python
latest = memory.get_latest(tag="decision")
if latest:
    print(f"Latest: {latest.thought}")
```

**Возвращает:** `Optional[TemporalReasoningNode]`

### `get_state_at(timestamp)`

Состояние знаний на определенный момент времени.

```python
from datetime import datetime, timedelta

yesterday = datetime.now() - timedelta(days=1)
old_state = memory.get_state_at(yesterday)
```

### `find_conflicts(tag)`

Найти потенциальные конфликты.

```python
conflicts = memory.find_conflicts(tag="auth")
if conflicts:
    print("Found conflicting knowledge!")
    for group in conflicts:
        for node in group:
            print(f"  Node {node.node_id}: {node.thought[:50]}")
```

---

## Visualization Methods

### `show_graph(mode="full")`

Вывести граф с timestamps.

```python
memory.show_graph(mode="full")   # С содержимым
memory.show_graph(mode="simple") # Только структура
```

**Пример вывода:**

```
=== Temporal Reasoning Graph ===
Session: sprint_1
Created: 2026-01-19 01:48
Nodes: 5 | Edges: 2

Node 1: [task] [Active] @01-19 01:48 #auth,architecture
  ├─→ Node 3
  │   Node 3: [evidence] [Active] @01-19 01:48 #auth by:DevOps

Node 2: [evidence] [Superseded→5] @01-19 01:48 #auth by:Architect
```

### `show_timeline()`

Хронологический вид.

```python
memory.show_timeline()
```

**Пример:**

```
=== Timeline ===

📅 2026-01-19
----------------------------------------
  01:48:08 ✓ Node 1 [task]
           Tags: auth, architecture
  01:48:08 ✗ Node 2 [evidence] (→5)
           Tags: auth, decision
  01:48:08 ✓ Node 5 [evidence]
           Tags: auth, decision
```

### `show_stats()`

Статистика памяти.

```python
memory.show_stats()
```

**Пример:**

```
=== Memory Statistics ===
Session: sprint_1
Age: 2.5 hours
Total nodes: 10
Active: 8
Superseded: 2
By participant: {'Architect': 4, 'Developer': 3, 'QA': 3}
Tags: ['auth', 'testing', 'implementation']
```

---

## Session Management

### `start_new_session(session_id=None)`

Начать новую сессию.

```python
memory.start_new_session("sprint_2")
# или auto-generated
memory.start_new_session()
```

### `session_id` (property)

Получить текущий session ID.

```python
print(f"Current session: {memory.session_id}")
```

---

## Persistence

### `save_memory(file_path)`

Сохранить с полными temporal данными.

```python
memory.save_memory("./memory_sprint1.json")
```

**Формат файла:**

```json
{
  "version": "temporal_v1",
  "saved_at": "2026-01-19T01:48:08",
  "default_participant": "Architect",
  "messages": [...],
  "graph": {
    "session_id": "sprint_1",
    "created_at": "2026-01-19T01:48:08",
    "nodes": {
      "1": {
        "node_id": 1,
        "kind": "task",
        "thought": "...",
        "created_at": "2026-01-19T01:48:08",
        "session_id": "sprint_1",
        "participant": "system",
        "tags": ["auth"],
        "supersedes": [],
        "superseded_by": null
      }
    },
    "edges": [...]
  }
}
```

### `load_memory(file_path)`

Загрузить память.

```python
memory.load_memory("./memory_sprint1.json")
```

---

## TemporalReasoningNode

### Поля

| Поле | Тип | Описание |
|------|-----|----------|
| `node_id` | `int` | Уникальный ID |
| `kind` | `str` | task, subtask, evidence, summary |
| `thought` | `str` | Содержимое |
| `related_turn_ids` | `List[int]` | Связь с сообщениями |
| `active` | `bool\|str` | True, False, "Flushed" |
| `created_at` | `datetime` | **Время создания** |
| `session_id` | `str` | **ID сессии** |
| `version` | `int` | **Версия** |
| `supersedes` | `List[int]` | **Какие узлы заменяет** |
| `superseded_by` | `int\|None` | **Кем заменён** |
| `tags` | `List[str]` | **Теги** |
| `participant` | `str` | **Кто создал** |

### Методы

```python
node.is_superseded()  # → bool
node.age_days()       # → float (дней с создания)
```

---

## Complete Example

```python
import asyncio
from memobrain_temporal import TemporalMemoBrain

async def main():
    memory = TemporalMemoBrain(
        api_key="your_key",
        base_url="https://api.z.ai/api/anthropic",
        model_name="GLM-4.5-Air",
        session_id="sprint_1",
    )

    # Initialize
    memory.init_memory("Build auth system", tags=["auth"])

    # Add knowledge from different participants
    memory.add_knowledge(
        "Use session-based auth",
        tags=["auth", "decision"],
        participant="Architect",
    )

    # Later: update decision
    memory.update_knowledge(
        old_node_id=2,
        new_content="Changed to JWT for scalability",
        participant="Architect",
    )

    # Query current state
    current = memory.get_current_knowledge(tag="decision")
    print(f"Current decision: {current[0].thought}")

    # View history
    memory.show_timeline()

    # Save
    memory.save_memory("auth_memory.json")

asyncio.run(main())
```
