# MemoBrain Usage Guide

## Quick Start

### Installation

```bash
cd memobrain
source .venv/bin/activate  # Activate virtual environment
```

### Basic Usage

```python
import asyncio
from memobrain_anthropic import MemoBrainAnthropic

async def main():
    memory = MemoBrainAnthropic(
        api_key="your_api_key",
        base_url="https://api.z.ai/api/anthropic",
        model_name="GLM-4.5-Air"
    )

    memory.init_memory("Your task description")

    await memory.memorize([
        {"role": "assistant", "content": "Agent thought..."},
        {"role": "user", "content": "Response..."}
    ])

    print(memory.graph.pretty_print())

asyncio.run(main())
```

---

## Configuration

### z.ai (Anthropic Format)

```python
memory = MemoBrainAnthropic(
    api_key="your_zai_api_key",
    base_url="https://api.z.ai/api/anthropic",
    model_name="GLM-4.5-Air"  # Fast, cheap
    # model_name="GLM-4.7"    # Best quality
)
```

### OpenAI

```python
from memobrain import MemoBrain

memory = MemoBrain(
    api_key="sk-...",
    base_url="https://api.openai.com/v1",
    model_name="gpt-4o"
)
```

### Local LLM (Ollama, vLLM)

```python
memory = MemoBrain(
    api_key="EMPTY",
    base_url="http://localhost:11434/v1",
    model_name="llama3"
)
```

---

## Patterns

### Pattern 1: Simple Agent Loop

```python
async def agent_loop(task: str):
    memory = MemoBrainAnthropic(...)
    memory.init_memory(task)

    while not is_complete:
        # Agent thinks
        thought = await llm.think(context)

        # Tool executes
        result = await tool.execute(thought)

        # Store in memory
        await memory.memorize([
            {"role": "assistant", "content": thought},
            {"role": "user", "content": result}
        ])

        # Update context
        context = memory.messages

    return memory.graph
```

### Pattern 2: Token Budget Management

```python
MAX_TOKENS = 32_000

async def managed_agent(task: str):
    memory = MemoBrainAnthropic(...)
    memory.init_memory(task)

    while not is_complete:
        await memory.memorize(episode)

        # Estimate current tokens
        token_count = estimate_tokens(memory.messages)

        if token_count > MAX_TOKENS * 0.8:  # 80% threshold
            print("Optimizing memory...")
            memory.messages = await memory.recall()

    return memory
```

### Pattern 3: Multi-Agent Collaboration

```python
async def multi_agent_research(task: str):
    memory = MemoBrainAnthropic(...)
    memory.init_memory(task)

    # Analyst agent contributes
    await memory.memorize([
        {"role": "Agent_Analyst", "content": "Analyzing requirements..."},
        {"role": "System", "content": "Requirements: auth, API, DB"}
    ])

    # Developer agent contributes
    await memory.memorize([
        {"role": "Agent_Developer", "content": "Proposing architecture..."},
        {"role": "System", "content": "Architecture: NestJS + Prisma"}
    ])

    # QA agent contributes
    await memory.memorize([
        {"role": "Agent_QA", "content": "Identifying test scenarios..."},
        {"role": "System", "content": "Tests: unit, integration, e2e"}
    ])

    return memory
```

### Pattern 4: Checkpoint and Resume

```python
async def resumable_task(task: str, checkpoint_path: str = None):
    memory = MemoBrainAnthropic(...)

    if checkpoint_path and os.path.exists(checkpoint_path):
        # Resume from checkpoint
        memory.load_memory(checkpoint_path)
        print(f"Resumed with {len(memory.graph.nodes)} nodes")
    else:
        # Start fresh
        memory.init_memory(task)

    try:
        while not is_complete:
            await memory.memorize(episode)

            # Periodic checkpoint
            if step % 10 == 0:
                memory.save_memory(checkpoint_path)

    except Exception as e:
        # Save on error
        memory.save_memory(checkpoint_path)
        raise

    return memory
```

### Pattern 5: Manual Graph Manipulation

```python
async def manual_evidence(memory: MemoBrainAnthropic):
    # Add evidence manually without LLM
    node = memory.graph.add_node(
        kind="evidence",
        thought=json.dumps([
            {"role": "manual", "content": "Verified by human review"}
        ]),
        related_turn_ids=[100, 101]
    )

    # Link to task
    memory.graph.add_edge(
        src=node.node_id,
        dst=1,  # Task node
        rationale="human verification"
    )
```

---

## Best Practices

### 1. Episode Structure

**Good:**
```python
await memory.memorize([
    {"role": "assistant", "content": "Searching for NestJS patterns..."},
    {"role": "user", "content": "Found: modular architecture, DI, guards..."}
])
```

**Avoid:**
```python
# Don't memorize single messages
await memory.memorize([
    {"role": "assistant", "content": "Thinking..."}
])  # Missing user response!
```

### 2. Task Initialization

**Good:**
```python
memory.init_memory(
    "Implement user authentication with JWT tokens, "
    "including login, logout, refresh token, and role-based access"
)
```

**Avoid:**
```python
memory.init_memory("auth")  # Too vague for good decomposition
```

### 3. When to Call recall()

**Call when:**
- Token count exceeds 70-80% of budget
- Before saving long-term checkpoint
- At logical task boundaries

**Avoid calling:**
- After every memorize (too expensive)
- With very few nodes (nothing to optimize)

### 4. Error Handling

```python
async def safe_memorize(memory, episode):
    try:
        await memory.memorize(episode)
    except json.JSONDecodeError:
        print("LLM returned invalid JSON, storing raw")
        memory.messages.extend(episode)
    except Exception as e:
        print(f"Memorize failed: {e}")
        # Continue without storing
```

### 5. Graph Inspection

```python
def inspect_memory(memory):
    print(f"=== Memory Status ===")
    print(f"Nodes: {len(memory.graph.nodes)}")
    print(f"Edges: {len(memory.graph.edges)}")
    print(f"Messages: {len(memory.messages)}")

    # Count by kind
    kinds = {}
    for node in memory.graph.nodes.values():
        kinds[node.kind] = kinds.get(node.kind, 0) + 1
    print(f"By kind: {kinds}")

    # Count active
    active = sum(1 for n in memory.graph.nodes.values() if n.active is True)
    print(f"Active: {active}")
```

---

## Troubleshooting

### Issue: JSON Decode Error

**Symptom:**
```
json.decoder.JSONDecodeError: Expecting value: line 1 column 1
```

**Cause:** LLM wrapped JSON in markdown code blocks

**Solution:** Use `MemoBrainAnthropic` which strips markdown automatically

### Issue: 404 NOT_FOUND

**Symptom:**
```
{"code":500,"msg":"404 NOT_FOUND","success":false}
```

**Cause:** Wrong model name or endpoint

**Solution:** Check model name (lowercase: `glm-4.5-air`, not `GLM-4.5-Air`)

### Issue: Insufficient Balance

**Symptom:**
```
Insufficient balance or no resource package
```

**Cause:** API credits depleted

**Solution:** Check account balance at provider dashboard

### Issue: Empty Graph After Recall

**Symptom:** All nodes marked inactive after recall

**Cause:** LLM aggressively folded everything

**Solution:** The first and last few messages are protected; check if graph was too small

---

## Testing

### Run Basic Test

```bash
cd memobrain
source .venv/bin/activate
python test_memobrain_anthropic.py
```

### Run Complex Scenario

```bash
python test_complex_scenario.py
```

### Manual Testing

```python
import asyncio
from memobrain_anthropic import MemoBrainAnthropic

async def test():
    m = MemoBrainAnthropic(
        api_key="your_key",
        base_url="https://api.z.ai/api/anthropic",
        model_name="GLM-4.5-Air"
    )
    m.init_memory("Test task")
    print(m.graph.pretty_print())

asyncio.run(test())
```

---

## Integration Examples

### With BMad Workflows

```python
# In BMad workflow context
async def bmad_workflow_memory():
    memory = MemoBrainAnthropic(...)
    memory.init_memory("Implement Epic: User Authentication")

    # Phase 1: Analysis
    await memory.memorize([
        {"role": "Analyst", "content": "Requirements gathered..."},
        {"role": "System", "content": "Specs documented in PRD"}
    ])

    # Phase 2: Architecture
    await memory.memorize([
        {"role": "Architect", "content": "Designing auth flow..."},
        {"role": "System", "content": "JWT + refresh tokens selected"}
    ])

    # Phase 3: Implementation
    await memory.memorize([
        {"role": "Developer", "content": "Implementing auth module..."},
        {"role": "System", "content": "Code complete, tests passing"}
    ])

    # Save workflow memory
    memory.save_memory("./_bmad-output/epic_auth_memory.json")
```

### As MCP Server (Future)

```python
# Potential MCP tool definitions
tools = [
    {
        "name": "memobrain_init",
        "description": "Initialize memory with task",
        "parameters": {"task": "string"}
    },
    {
        "name": "memobrain_store",
        "description": "Store reasoning episode",
        "parameters": {"episode": "array"}
    },
    {
        "name": "memobrain_recall",
        "description": "Optimize and retrieve memory",
        "parameters": {}
    }
]
```
