# MemoBrain API Reference

## Classes

### MemoBrain (OpenAI SDK)

```python
from memobrain import MemoBrain
```

### MemoBrainAnthropic (Anthropic SDK)

```python
from memobrain_anthropic import MemoBrainAnthropic
```

---

## Constructor

### `MemoBrain.__init__(api_key, base_url, model_name)`

Initialize MemoBrain instance.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `api_key` | `str` | API key for LLM provider |
| `base_url` | `str` | Base URL for API endpoint |
| `model_name` | `str` | Model identifier |

**Example (OpenAI):**

```python
memory = MemoBrain(
    api_key="sk-...",
    base_url="https://api.openai.com/v1",
    model_name="gpt-4"
)
```

**Example (z.ai with Anthropic SDK):**

```python
memory = MemoBrainAnthropic(
    api_key="your_zai_key",
    base_url="https://api.z.ai/api/anthropic",
    model_name="GLM-4.5-Air"  # or "GLM-4.7"
)
```

---

## Core Methods

### `init_memory(task)`

Initialize the memory graph with a main task.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `task` | `str` | Task description / main objective |

**Returns:** `None`

**Example:**

```python
memory.init_memory("Research and implement authentication system")
```

**Effect:**
- Creates root node with `kind="task"`
- Sets `related_turn_ids=[0, 1]`
- Graph has 1 node, 0 edges

---

### `async memorize(new_messages)`

Store new reasoning episodes in memory.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `new_messages` | `List[Dict]` | List of message dicts with `role` and `content` |

**Returns:** `None`

**Example:**

```python
await memory.memorize([
    {"role": "assistant", "content": "I'll search for authentication patterns..."},
    {"role": "user", "content": "Search results: JWT is recommended for..."}
])
```

**Message Format:**

```python
[
    {"role": "assistant", "content": "<agent reasoning/action>"},
    {"role": "user", "content": "<tool response/feedback>"}
]
```

**Processing:**
1. Messages added to internal `self.messages` list
2. Grouped into pairs (assistant + user)
3. Each pair sent to LLM for patch generation
4. Patch applied to graph (new nodes + edges)

**LLM Calls:** 1 per message pair

---

### `async recall()`

Optimize memory by flushing redundant nodes and folding completed paths.

**Parameters:** None

**Returns:** `List[Dict]` - Optimized message list

**Example:**

```python
optimized_messages = await memory.recall()
print(f"Reduced from {len(memory.messages)} to {len(optimized_messages)}")
```

**Processing:**
1. Current graph sent to LLM for analysis
2. LLM identifies flush/fold operations
3. Operations applied to graph
4. Optimized message list generated

**LLM Calls:** 1

---

## Persistence Methods

### `save_memory(file_path)`

Save memory graph to JSON file.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `file_path` | `str` | Path to save JSON file |

**Returns:** `None`

**Example:**

```python
memory.save_memory("./checkpoints/memory_v1.json")
```

---

### `load_memory(file_path)`

Load memory graph from JSON file.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `file_path` | `str` | Path to JSON file |

**Returns:** `None`

**Example:**

```python
memory.load_memory("./checkpoints/memory_v1.json")
```

---

### `load_dict_memory(graph_dict)`

Load memory graph from dictionary.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `graph_dict` | `Dict` | Graph as dictionary (from `to_dict()`) |

**Returns:** `None`

**Example:**

```python
import json
with open("memory.json") as f:
    data = json.load(f)
memory.load_dict_memory(data["memory"])
```

---

## ReasoningGraph Methods

Access via `memory.graph`:

### `graph.add_node(kind, thought, related_turn_ids)`

Manually add a node.

```python
node = memory.graph.add_node(
    kind="evidence",
    thought="Manual finding...",
    related_turn_ids=[10, 11]
)
print(f"Created node {node.node_id}")
```

### `graph.add_edge(src, dst, rationale)`

Manually add an edge.

```python
memory.graph.add_edge(
    src=new_node.node_id,
    dst=1,  # Link to task
    rationale="supports main task"
)
```

### `graph.pretty_print(mode)`

Get human-readable graph representation.

| Mode | Output |
|------|--------|
| `"full"` | Nodes with full thought content |
| `"simple"` | Nodes without content |

```python
print(memory.graph.pretty_print(mode="full"))
```

### `graph.to_dict()`

Export graph to dictionary.

```python
data = memory.graph.to_dict()
# {"nodes": {...}, "edges": [...]}
```

### `graph.get_leaf_node_ids()`

Get IDs of nodes with no outgoing edges.

```python
leaves = memory.graph.get_leaf_node_ids()
# [4, 5, 6] - evidence nodes at end of paths
```

---

## Properties

### `memory.graph`

Access the underlying `ReasoningGraph` instance.

```python
print(f"Nodes: {len(memory.graph.nodes)}")
print(f"Edges: {len(memory.graph.edges)}")
```

### `memory.messages`

Access raw message history.

```python
print(f"Total messages: {len(memory.messages)}")
```

### `memory.model_name`

Get configured model name.

```python
print(f"Using model: {memory.model_name}")
```

---

## Error Handling

### Retry Logic

Both `memorize()` and `recall()` include retry logic:

```python
max_retries = 3
for attempt in range(max_retries):
    try:
        response = await self._create_completion(...)
        break
    except Exception as e:
        if attempt < max_retries - 1:
            await asyncio.sleep(3)  # Wait before retry
        else:
            raise
```

### JSON Parsing

LLM responses are parsed as JSON. If parsing fails:

```python
try:
    patch_json = json.loads(response)
except Exception as e:
    print("JSON decode error:", e)
    print("Raw content:", response)
    raise e
```

### Markdown Stripping (Anthropic version)

GLM models may wrap JSON in markdown code blocks:

```python
def _strip_markdown_json(self, text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()
```

---

## Complete Example

```python
import asyncio
from memobrain_anthropic import MemoBrainAnthropic

async def main():
    # Initialize
    memory = MemoBrainAnthropic(
        api_key="your_key",
        base_url="https://api.z.ai/api/anthropic",
        model_name="GLM-4.5-Air"
    )

    # Set task
    memory.init_memory("Build REST API for user management")

    # Store reasoning episodes
    await memory.memorize([
        {"role": "assistant", "content": "First, I'll design the data model..."},
        {"role": "user", "content": "User model: id, email, name, created_at"}
    ])

    await memory.memorize([
        {"role": "assistant", "content": "Now implementing CRUD endpoints..."},
        {"role": "user", "content": "Endpoints: GET/POST/PUT/DELETE /users"}
    ])

    # Check graph
    print(memory.graph.pretty_print())

    # Optimize if needed
    if len(memory.messages) > 20:
        optimized = await memory.recall()

    # Save checkpoint
    memory.save_memory("./api_project_memory.json")

asyncio.run(main())
```
