# Temporal Knowledge Management

## Проблема

При долгосрочном использовании памяти возникает проблема **противоречивых утверждений**:

```
День 1: "Аутентификация реализована через сессии"
День 30: "Аутентификация переделана на JWT токены"
```

Оба утверждения присутствуют в памяти, но второе **более актуально**.

---

## Текущее состояние MemoBrain

### Что есть сейчас

В оригинальной реализации:

```python
@dataclass
class ReasoningNode:
    node_id: int
    kind: NodeKind
    thought: str
    related_turn_ids: List[int]  # ← Только порядок в разговоре
    active: bool
```

**Ограничения:**
- `related_turn_ids` - только порядковый номер в сессии
- Нет абсолютных timestamps
- Нет версионирования знаний
- Нет механизма разрешения конфликтов

---

## Рекомендуемые расширения

### 1. Добавить Timestamp к узлам

```python
from datetime import datetime

@dataclass
class TemporalReasoningNode:
    node_id: int
    kind: NodeKind
    thought: str
    related_turn_ids: List[int]
    active: bool
    # NEW: Temporal fields
    created_at: datetime           # Когда создано
    session_id: str                # ID сессии (день/sprint)
    version: int = 1               # Версия знания
    supersedes: List[int] = None   # Какие узлы это заменяет
```

### 2. Механизм "Supersedes"

```
Node 5 [evidence] "Auth via sessions" (created: 2026-01-01)
    ↓ superseded by
Node 42 [evidence] "Auth via JWT" (created: 2026-01-30, supersedes: [5])
```

При запросе знаний - игнорировать superseded узлы.

### 3. Временные запросы

```python
def get_knowledge_at(self, timestamp: datetime) -> List[ReasoningNode]:
    """Получить состояние знаний на определенную дату"""
    return [
        node for node in self.nodes.values()
        if node.created_at <= timestamp
        and not self._is_superseded_at(node, timestamp)
    ]

def get_latest_on_topic(self, topic: str) -> ReasoningNode:
    """Получить самое свежее утверждение по теме"""
    relevant = self.search_by_topic(topic)
    return max(relevant, key=lambda n: n.created_at)
```

---

## Практический подход (без модификации кода)

Пока не модифицируем код, можно использовать **соглашения в данных**:

### Соглашение 1: Prefix в content

```python
await memory.memorize([
    {"role": "assistant", "content": "[2026-01-30] Researching auth..."},
    {"role": "user", "content": "[2026-01-30] JWT selected for auth"}
])
```

### Соглашение 2: Metadata в role

```python
await memory.memorize([
    {"role": "Agent_Architect@2026-01-30", "content": "JWT architecture..."},
    {"role": "System@2026-01-30", "content": "Decision recorded"}
])
```

### Соглашение 3: Tags в content

```python
await memory.memorize([
    {"role": "assistant", "content": "#auth #decision @2026-01-30 Using JWT tokens"},
    {"role": "user", "content": "#auth #implemented @2026-01-30 JWT module done"}
])
```

---

## Разрешение конфликтов

### Стратегия: Latest Wins

При конфликте - побеждает **последнее по времени** утверждение:

```python
def resolve_conflict(statements: List[Node]) -> Node:
    """Простая стратегия: последнее = верное"""
    return max(statements, key=lambda n: n.created_at)
```

### Стратегия: Explicit Override

Явно указывать, что новое знание заменяет старое:

```python
await memory.memorize([
    {
        "role": "assistant",
        "content": "[SUPERSEDES node_5] Auth changed from sessions to JWT"
    },
    {"role": "user", "content": "Change recorded, node_5 marked obsolete"}
])
```

### Стратегия: Versioned Topics

Версионировать знания по темам:

```
auth_v1: Sessions
auth_v2: JWT (current)
auth_v3: OAuth2 (planned)
```

---

## Пример: Эволюция проекта

```
=== Session 1 (2026-01-01) ===
Node 1: [task] "Build WB Repricer"
Node 2: [evidence] "Using REST API" (created: 2026-01-01)

=== Session 5 (2026-01-15) ===
Node 15: [evidence] "Adding WebSocket for realtime" (created: 2026-01-15)
Node 16: [evidence] "REST + WebSocket hybrid" (supersedes: [2])

=== Session 10 (2026-01-30) ===
Node 30: [evidence] "Switching to GraphQL" (created: 2026-01-30)
Node 31: [evidence] "GraphQL replaces REST" (supersedes: [2, 16])

=== Current State ===
Active knowledge:
- Node 30: GraphQL is the API (latest)
- Node 15: WebSocket for realtime (not superseded)

Obsolete:
- Node 2: REST API (superseded by 31)
- Node 16: REST + WebSocket (superseded by 31)
```

---

## Рекомендации

### Для краткосрочного использования

1. Используйте timestamp prefix в content
2. Группируйте сессии по дням/спринтам
3. Периодически делайте "snapshot" актуального состояния

### Для долгосрочного использования

1. Расширить ReasoningNode с temporal fields
2. Реализовать механизм supersedes
3. Добавить "temporal queries" в API
4. Создать "consolidation" процесс для очистки устаревших знаний

### При запросах к памяти

```python
# Плохо: получить всё
all_evidence = memory.get_by_kind("evidence")

# Хорошо: получить актуальное
recent_evidence = [
    e for e in memory.get_by_kind("evidence")
    if not is_superseded(e)
]
```

---

## Интеграция с BMad

В контексте BMad workflows:

```
Epic 1 (Sprint 1): Auth via sessions
    → Story 1.1: Implement sessions ✓

Epic 1 (Sprint 3): Auth refactored to JWT
    → Story 1.5: Migrate to JWT ✓
    → Supersedes: Story 1.1

Memory query: "How is auth implemented?"
→ Return: "JWT tokens (as of Sprint 3)"
→ Note: "Previously was sessions (Sprint 1, superseded)"
```

---

## Будущие улучшения

1. **Temporal Index**: Индекс по времени для быстрых запросов
2. **Conflict Detection**: Автоматическое обнаружение противоречий
3. **Knowledge Graph Versioning**: Git-like версионирование графа
4. **Decay Function**: Автоматическое снижение "веса" старых знаний
