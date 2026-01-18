#!/usr/bin/env python3
"""
Test Temporal MemoBrain - Knowledge evolution and versioning
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from memobrain_temporal import TemporalMemoBrain

# z.ai Configuration (from .env or environment)
API_KEY = os.environ.get("ZAI_API_KEY", "your_api_key_here")
BASE_URL = os.environ.get("ZAI_BASE_URL", "https://api.z.ai/api/anthropic")
MODEL_NAME = os.environ.get("ZAI_MODEL", "GLM-4.5-Air")


async def test_temporal_features():
    print("\n" + "=" * 70)
    print("  TEMPORAL MEMOBRAIN TEST")
    print("  Testing knowledge evolution and versioning")
    print("=" * 70)

    # Initialize
    memory = TemporalMemoBrain(
        api_key=API_KEY,
        base_url=BASE_URL,
        model_name=MODEL_NAME,
        session_id="sprint_1",
        default_participant="Architect",
    )

    # ==================== Test 1: Basic temporal tracking ====================
    print("\n" + "-" * 70)
    print("TEST 1: Basic Temporal Tracking")
    print("-" * 70)

    memory.init_memory(
        "Design authentication system for WB Repricer",
        tags=["auth", "architecture"]
    )

    # Add initial knowledge
    node1 = memory.add_knowledge(
        content="Authentication will use session-based approach with Redis storage",
        kind="evidence",
        tags=["auth", "decision"],
        participant="Architect",
    )
    print(f"✓ Added initial auth decision (Node {node1})")

    # Show graph with timestamps
    print("\nGraph after initial setup:")
    memory.show_graph(mode="simple")

    # ==================== Test 2: Knowledge from multiple participants ====================
    print("\n" + "-" * 70)
    print("TEST 2: Multi-Participant Knowledge")
    print("-" * 70)

    await asyncio.sleep(0.1)  # Small delay for timestamp difference

    node2 = memory.add_knowledge(
        content="Session storage should handle 10,000 concurrent users",
        kind="evidence",
        tags=["auth", "performance"],
        participant="DevOps",
        link_to=1,  # Link to task
    )
    print(f"✓ DevOps added performance requirement (Node {node2})")

    await asyncio.sleep(0.1)

    node3 = memory.add_knowledge(
        content="Need unit tests for session management with 80% coverage",
        kind="evidence",
        tags=["auth", "testing"],
        participant="QA",
        link_to=1,
    )
    print(f"✓ QA added testing requirement (Node {node3})")

    print("\nGraph with multiple participants:")
    memory.show_graph(mode="simple")

    # ==================== Test 3: Knowledge supersedes ====================
    print("\n" + "-" * 70)
    print("TEST 3: Knowledge Evolution (Supersedes)")
    print("-" * 70)

    print(f"\nOriginal decision (Node {node1}):")
    original = memory.graph.nodes[node1]
    print(f"  Content: {original.thought[:60]}...")
    print(f"  Created: {original.created_at.strftime('%H:%M:%S')}")

    # Architect changes decision
    await asyncio.sleep(0.1)
    node4 = memory.update_knowledge(
        old_node_id=node1,
        new_content="Authentication changed to JWT tokens for better scalability and stateless operation",
        participant="Architect",
    )
    print(f"\n✓ Architect updated decision (Node {node4} supersedes Node {node1})")

    print(f"\nNew decision (Node {node4}):")
    new_node = memory.graph.nodes[node4]
    print(f"  Content: {new_node.thought[:60]}...")
    print(f"  Supersedes: {new_node.supersedes}")

    print(f"\nOld decision status (Node {node1}):")
    old_node = memory.graph.nodes[node1]
    print(f"  Superseded by: {old_node.superseded_by}")

    # ==================== Test 4: Temporal queries ====================
    print("\n" + "-" * 70)
    print("TEST 4: Temporal Queries")
    print("-" * 70)

    # Get current knowledge for auth
    print("\nCurrent knowledge for #auth (excluding superseded):")
    current = memory.get_current_knowledge(tag="auth")
    for node in current:
        print(f"  Node {node.node_id}: {node.thought[:50]}...")

    # Get history
    print("\nFull history for #auth (including superseded):")
    history = memory.get_knowledge_history(tag="auth")
    for node in history:
        status = "✓ current" if not node.is_superseded() else f"✗ superseded→{node.superseded_by}"
        print(f"  [{node.created_at.strftime('%H:%M:%S')}] Node {node.node_id}: {status}")

    # Get latest
    print("\nLatest knowledge for #decision:")
    latest = memory.get_latest(tag="decision")
    if latest:
        print(f"  Node {latest.node_id}: {latest.thought[:60]}...")

    # ==================== Test 5: Timeline view ====================
    print("\n" + "-" * 70)
    print("TEST 5: Timeline View")
    print("-" * 70)

    memory.show_timeline()

    # ==================== Test 6: Statistics ====================
    print("\n" + "-" * 70)
    print("TEST 6: Statistics")
    print("-" * 70)

    memory.show_stats()

    # ==================== Test 7: Persistence ====================
    print("\n" + "-" * 70)
    print("TEST 7: Persistence")
    print("-" * 70)

    save_path = os.path.join(os.path.dirname(__file__), "temporal_memory_test.json")
    memory.save_memory(save_path)
    print(f"✓ Saved to: {save_path}")

    # Load into new instance
    memory2 = TemporalMemoBrain(
        api_key=API_KEY,
        base_url=BASE_URL,
        model_name=MODEL_NAME,
    )
    memory2.load_memory(save_path)
    print(f"✓ Loaded into new instance")
    print(f"  Nodes: {len(memory2.graph.nodes)}")
    print(f"  Session: {memory2.session_id}")

    # ==================== Test 8: LLM-based memorize ====================
    print("\n" + "-" * 70)
    print("TEST 8: LLM-based Memorize (with timestamps)")
    print("-" * 70)

    await memory.memorize(
        new_messages=[
            {"role": "assistant", "content": "Implementing JWT token generation with RS256 algorithm"},
            {"role": "user", "content": "JWT implementation complete. Using jose library for signing."}
        ],
        tags=["auth", "implementation"],
        participant="Developer",
    )
    print("✓ Developer added implementation details via LLM")

    print("\nFinal graph:")
    memory.show_graph(mode="simple")

    # ==================== Summary ====================
    print("\n" + "=" * 70)
    print("  TEST COMPLETED")
    print("=" * 70)

    stats = memory.graph.stats()
    print(f"""
    Summary:
    ────────
    Total nodes: {stats['total_nodes']}
    Active: {stats['active_nodes']}
    Superseded: {stats['superseded_nodes']}
    Participants: {list(stats['by_participant'].keys())}
    Tags: {stats['unique_tags']}
    """)


if __name__ == "__main__":
    asyncio.run(test_temporal_features())
