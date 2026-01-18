# MemoBrain Architecture

## Overview

MemoBrain is an executive memory system for LLM-based agents that manages reasoning trajectories through a **Reasoning Graph** structure. Unlike simple context accumulation, it actively organizes, compresses, and optimizes reasoning steps.

## Core Philosophy

```
┌─────────────────────────────────────────────────────────────┐
│                    MEMOBRAIN SYSTEM                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   [Agent Loop]  ──memorize()──>  [Reasoning Graph]          │
│        │                              │                      │
│        │                              ▼                      │
│        │                    ┌─────────────────┐              │
│        │                    │  LLM Analysis   │              │
│        │                    │  (generate      │              │
│        │                    │   patches)      │              │
│        │                    └─────────────────┘              │
│        │                              │                      │
│        │                              ▼                      │
│        │                    ┌─────────────────┐              │
│        │                    │  Graph Update   │              │
│        │                    │  (add nodes,    │              │
│        │                    │   add edges)    │              │
│        │                    └─────────────────┘              │
│        │                              │                      │
│        ◄────────recall()─────────────┘                      │
│   (optimized                                                 │
│    messages)                                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

1. **Input**: Agent reasoning episodes (assistant thought + tool response)
2. **Processing**: LLM analyzes and generates graph patches
3. **Storage**: Nodes and edges added to ReasoningGraph
4. **Optimization**: recall() triggers flush/fold operations
5. **Output**: Optimized message list for continued reasoning

---

## Component Diagram

```
memobrain/
├── src/
│   ├── memobrain.py          # Main MemoBrain class (OpenAI SDK)
│   ├── memobrain_anthropic.py # Anthropic SDK version (z.ai compatible)
│   ├── problem_tree.py       # ReasoningGraph implementation
│   ├── schema.py             # Pydantic models for operations
│   └── prompts.py            # System prompts for LLM
├── examples/
│   ├── example_usage.py      # Basic usage demo
│   ├── react_with_memory.py  # Full ReAct agent integration
│   └── memory_snapshot.json  # Sample memory graph
└── docs/
    ├── ARCHITECTURE.md       # This file
    ├── DATA-MODEL.md         # Data structures
    ├── API-REFERENCE.md      # API documentation
    └── USAGE-GUIDE.md        # How to use
```

---

## Key Design Decisions

### 1. Graph-Based Memory (not Linear)

Unlike simple message history, MemoBrain uses a **directed graph** where:
- Nodes represent reasoning steps (tasks, subtasks, evidence)
- Edges represent relationships (decompose, refine, support)
- Dependencies are explicitly tracked

### 2. LLM-Driven Organization

The system uses LLM calls to:
- Analyze new reasoning episodes
- Decide how to integrate into existing graph
- Identify redundant or completed paths
- Generate summaries for compression

### 3. Episodic Memory Units

Recommended memory unit is an **episode**:
```
[assistant thought] + [tool/user response]
```

This captures the full reasoning cycle.

### 4. Lazy Optimization

Memory is accumulated without optimization until:
- Token budget exceeded
- Explicit `recall()` called
- Context window pressure detected

---

## Integration Points

### With Agent Loops

```python
# Inside agent loop
while not done:
    thought = llm.think(context)
    result = tool.execute(thought)

    # Store episode
    await memory.memorize([
        {"role": "assistant", "content": thought},
        {"role": "user", "content": result}
    ])

    # Optimize if needed
    if token_count > budget:
        context = await memory.recall()
```

### With Multi-Agent Systems

The `role` field in Notes supports multiple participants:
```python
# Agent 1 contributes
await memory.memorize([
    {"role": "Agent_Analyst", "content": "Found pattern..."},
    {"role": "System", "content": "Analysis stored."}
])

# Agent 2 contributes
await memory.memorize([
    {"role": "Agent_Developer", "content": "Implementation approach..."},
    {"role": "System", "content": "Approach recorded."}
])
```

---

## Performance Characteristics

| Operation | Complexity | LLM Calls |
|-----------|------------|-----------|
| `init_memory()` | O(1) | 0 |
| `memorize()` | O(n) per episode | 1 per pair |
| `recall()` | O(n) | 1 |
| `save_memory()` | O(n) | 0 |
| `load_memory()` | O(n) | 0 |

Where n = number of nodes in graph.

---

## Limitations

1. **LLM Dependency**: Requires LLM calls for memorize/recall
2. **JSON Parsing**: LLM must produce valid JSON (may need retries)
3. **Single Session**: Graph is session-scoped (persistence via save/load)
4. **No Concurrent Access**: Not thread-safe by default
