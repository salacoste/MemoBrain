#!/usr/bin/env python3
"""
MemoBrain Test Script - Validates connection with z.ai GLM models
"""

import asyncio
import sys
import os

# Use installed package (from .venv)
from memobrain import MemoBrain

# Configuration for z.ai
import os
API_KEY = os.environ.get("ZAI_API_KEY", "your_api_key_here")

# z.ai OpenAI-compatible endpoint
BASE_URL = "https://api.z.ai/api/openai/v1"

# Available models (mapped from Anthropic names)
MODELS = {
    "opus": "GLM-4.7",      # Best quality
    "sonnet": "GLM-4.7",    # Good balance
    "haiku": "GLM-4.5-Air"  # Fast/cheap
}

# Use haiku-equivalent for testing (faster, cheaper)
MODEL_NAME = MODELS["haiku"]


async def test_basic_connection():
    """Test 1: Basic API connection"""
    print("\n" + "="*60)
    print("TEST 1: Basic API Connection")
    print("="*60)

    memory = MemoBrain(
        api_key=API_KEY,
        base_url=BASE_URL,
        model_name=MODEL_NAME
    )

    print(f"✓ MemoBrain initialized")
    print(f"  - Base URL: {BASE_URL}")
    print(f"  - Model: {MODEL_NAME}")

    return memory


async def test_init_memory(memory: MemoBrain):
    """Test 2: Initialize memory with a task"""
    print("\n" + "="*60)
    print("TEST 2: Initialize Memory")
    print("="*60)

    task = "Research and summarize the key features of MemoBrain system"
    memory.init_memory(task)

    print(f"✓ Memory initialized with task")
    print(f"  - Task: {task[:50]}...")
    print(f"  - Graph nodes: {len(memory.graph.nodes)}")
    print(f"  - Graph edges: {len(memory.graph.edges)}")

    # Show initial graph
    print("\nInitial Graph:")
    print(memory.graph.pretty_print())


async def test_memorize(memory: MemoBrain):
    """Test 3: Store reasoning episodes"""
    print("\n" + "="*60)
    print("TEST 3: Memorize Reasoning Episodes")
    print("="*60)

    # Simulate a reasoning episode (agent thought + tool response)
    episode1 = [
        {"role": "assistant", "content": "I need to search for information about MemoBrain's architecture. Let me search for 'MemoBrain memory system architecture'."},
        {"role": "user", "content": "Search results: MemoBrain is an executive memory system with three core mechanisms: Prune, Fold, and Context Management. It uses a reasoning graph to track dependencies."}
    ]

    print("Memorizing episode 1...")
    try:
        await memory.memorize(episode1)
        print(f"✓ Episode 1 memorized")
        print(f"  - Graph nodes: {len(memory.graph.nodes)}")
        print(f"  - Graph edges: {len(memory.graph.edges)}")
    except Exception as e:
        print(f"✗ Error memorizing episode 1: {e}")
        return False

    # Second episode
    episode2 = [
        {"role": "assistant", "content": "Now I need to understand how the optimization works. Let me search for 'MemoBrain flush and fold operations'."},
        {"role": "user", "content": "Search results: Flush removes redundant nodes, Fold compresses completed reasoning paths into summaries while preserving semantic content."}
    ]

    print("Memorizing episode 2...")
    try:
        await memory.memorize(episode2)
        print(f"✓ Episode 2 memorized")
        print(f"  - Graph nodes: {len(memory.graph.nodes)}")
        print(f"  - Graph edges: {len(memory.graph.edges)}")
    except Exception as e:
        print(f"✗ Error memorizing episode 2: {e}")
        return False

    # Show current graph
    print("\nCurrent Graph:")
    print(memory.graph.pretty_print())

    return True


async def test_recall(memory: MemoBrain):
    """Test 4: Recall (optimize) memory"""
    print("\n" + "="*60)
    print("TEST 4: Recall (Optimize Memory)")
    print("="*60)

    print("Calling recall() to optimize memory...")
    try:
        optimized = await memory.recall()
        print(f"✓ Memory optimized")
        print(f"  - Original messages: {len(memory.messages)}")
        print(f"  - Optimized messages: {len(optimized)}")

        print("\nOptimized Graph:")
        print(memory.graph.pretty_print())

        return optimized
    except Exception as e:
        print(f"✗ Error during recall: {e}")
        return None


async def test_persistence(memory: MemoBrain):
    """Test 5: Save and load memory"""
    print("\n" + "="*60)
    print("TEST 5: Persistence (Save/Load)")
    print("="*60)

    save_path = os.path.join(os.path.dirname(__file__), "test_memory_snapshot.json")

    # Save
    memory.save_memory(save_path)
    print(f"✓ Memory saved to: {save_path}")

    # Load into new instance
    new_memory = MemoBrain(
        api_key=API_KEY,
        base_url=BASE_URL,
        model_name=MODEL_NAME
    )
    new_memory.load_memory(save_path)

    print(f"✓ Memory loaded into new instance")
    print(f"  - Nodes: {len(new_memory.graph.nodes)}")
    print(f"  - Edges: {len(new_memory.graph.edges)}")

    # Cleanup
    os.remove(save_path)
    print(f"✓ Test file cleaned up")


async def main():
    print("\n" + "="*60)
    print("  MemoBrain Test Suite")
    print("  Testing with z.ai GLM Models")
    print("="*60)

    try:
        # Test 1: Connection
        memory = await test_basic_connection()

        # Test 2: Init
        await test_init_memory(memory)

        # Test 3: Memorize (requires API call)
        success = await test_memorize(memory)

        if success:
            # Test 4: Recall (requires API call)
            await test_recall(memory)

            # Test 5: Persistence
            await test_persistence(memory)

        print("\n" + "="*60)
        print("  TEST SUITE COMPLETED")
        print("="*60)

    except Exception as e:
        print(f"\n✗ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
