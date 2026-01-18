#!/usr/bin/env python3
"""
MemoBrain Complex Scenario Test
Simulates a realistic multi-step research task with 8 reasoning episodes
to demonstrate memory optimization at scale.
"""

import asyncio
import sys
import os
import json

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from memobrain_anthropic import MemoBrainAnthropic

# z.ai Configuration (from .env or environment)
API_KEY = os.environ.get("ZAI_API_KEY", "your_api_key_here")
BASE_URL = os.environ.get("ZAI_BASE_URL", "https://api.z.ai/api/anthropic")
MODEL_NAME = os.environ.get("ZAI_MODEL", "GLM-4.7")  # Using best model for complex reasoning


def count_tokens_estimate(messages: list) -> int:
    """Rough token estimate (4 chars ≈ 1 token)"""
    total_chars = sum(len(m.get("content", "")) for m in messages)
    return total_chars // 4


async def run_complex_scenario():
    print("\n" + "=" * 70)
    print("  MEMOBRAIN COMPLEX SCENARIO TEST")
    print("  Simulating: 'Research NestJS Best Practices for Production'")
    print("=" * 70)

    # Initialize
    memory = MemoBrainAnthropic(
        api_key=API_KEY,
        base_url=BASE_URL,
        model_name=MODEL_NAME
    )

    task = """Research and compile a comprehensive guide on NestJS best practices
    for production applications, including: architecture patterns, error handling,
    logging, testing strategies, and deployment considerations."""

    memory.init_memory(task)
    print(f"\n✓ Task initialized")
    print(f"  Task: {task[:60]}...")

    # Simulate 8 reasoning episodes (typical research session)
    episodes = [
        # Episode 1: Initial architecture search
        [
            {"role": "assistant", "content": "I'll start by researching NestJS architecture patterns. Let me search for 'NestJS modular architecture best practices 2024'."},
            {"role": "user", "content": "Search results: NestJS recommends a modular architecture with feature modules. Key patterns include: 1) Domain-driven design with bounded contexts, 2) Shared modules for common functionality, 3) Dynamic modules for configurable providers, 4) Circular dependency avoidance through forwardRef()."}
        ],
        # Episode 2: Deep dive into modules
        [
            {"role": "assistant", "content": "Good foundation. Now let me explore module organization in detail. Searching for 'NestJS module organization enterprise patterns'."},
            {"role": "user", "content": "Search results: Enterprise NestJS apps typically use: CoreModule (singleton services), SharedModule (pipes, guards, interceptors), FeatureModules (domain logic). Best practice is to keep modules focused and use barrel exports. Avoid god modules with too many providers."}
        ],
        # Episode 3: Error handling
        [
            {"role": "assistant", "content": "Now I need to research error handling. Searching for 'NestJS error handling exception filters production'."},
            {"role": "user", "content": "Search results: Production error handling requires: 1) Global exception filter for consistent error responses, 2) Custom HttpException classes for domain errors, 3) Error serialization that hides internal details, 4) Integration with logging for debugging, 5) Proper HTTP status codes mapping."}
        ],
        # Episode 4: Logging strategies
        [
            {"role": "assistant", "content": "Error handling links to logging. Let me search for 'NestJS logging best practices Winston Pino production'."},
            {"role": "user", "content": "Search results: For production logging: 1) Use structured logging (JSON format) with Pino or Winston, 2) Implement request correlation IDs, 3) Log levels: error for exceptions, warn for recoverable issues, info for business events, debug for development, 4) Avoid logging sensitive data, 5) Use log aggregation (ELK, Datadog)."}
        ],
        # Episode 5: Testing strategies
        [
            {"role": "assistant", "content": "Testing is crucial. Searching for 'NestJS testing strategies unit integration e2e best practices'."},
            {"role": "user", "content": "Search results: NestJS testing pyramid: 1) Unit tests with Jest for services/controllers (mock dependencies), 2) Integration tests for module interactions, 3) E2E tests with supertest for API contracts, 4) Use Test.createTestingModule for isolated testing, 5) Database testing with in-memory SQLite or test containers."}
        ],
        # Episode 6: Database patterns
        [
            {"role": "assistant", "content": "Database handling is important too. Searching for 'NestJS TypeORM Prisma repository pattern production'."},
            {"role": "user", "content": "Search results: Database best practices: 1) Repository pattern for data access abstraction, 2) Prisma gaining popularity over TypeORM for type safety, 3) Use transactions for complex operations, 4) Connection pooling configuration, 5) Migration strategies for zero-downtime deployments, 6) Soft deletes for audit trails."}
        ],
        # Episode 7: Security
        [
            {"role": "assistant", "content": "Security is essential for production. Searching for 'NestJS security best practices authentication authorization'."},
            {"role": "user", "content": "Search results: Security essentials: 1) Helmet middleware for HTTP headers, 2) Rate limiting with @nestjs/throttler, 3) CORS configuration, 4) JWT with refresh tokens for auth, 5) Role-based access control (RBAC) with guards, 6) Input validation with class-validator, 7) SQL injection prevention through ORMs."}
        ],
        # Episode 8: Deployment
        [
            {"role": "assistant", "content": "Finally, deployment considerations. Searching for 'NestJS deployment Docker Kubernetes production configuration'."},
            {"role": "user", "content": "Search results: Deployment best practices: 1) Multi-stage Docker builds for small images, 2) Environment-based configuration with @nestjs/config, 3) Health checks for container orchestration, 4) Graceful shutdown handling, 5) PM2 or Docker for process management, 6) CI/CD with automated testing gates."}
        ]
    ]

    # Process each episode
    print("\n" + "-" * 70)
    print("PHASE 1: Memorizing Episodes")
    print("-" * 70)

    for i, episode in enumerate(episodes, 1):
        print(f"\n📝 Episode {i}/8: ", end="")
        await memory.memorize(episode)
        print(f"✓ (Nodes: {len(memory.graph.nodes)}, Edges: {len(memory.graph.edges)})")

    # Show graph before optimization
    print("\n" + "-" * 70)
    print("GRAPH BEFORE OPTIMIZATION")
    print("-" * 70)
    print(memory.graph.pretty_print(mode="simple"))

    # Statistics before
    total_messages = len(memory.messages)
    tokens_before = count_tokens_estimate(memory.messages)
    nodes_before = len(memory.graph.nodes)

    print(f"\n📊 Statistics Before Optimization:")
    print(f"   - Total messages: {total_messages}")
    print(f"   - Estimated tokens: ~{tokens_before}")
    print(f"   - Graph nodes: {nodes_before}")
    print(f"   - Graph edges: {len(memory.graph.edges)}")

    # Optimize with recall
    print("\n" + "-" * 70)
    print("PHASE 2: Memory Optimization (recall)")
    print("-" * 70)
    print("\n⚙️  Running recall() to optimize memory...")

    optimized_messages = await memory.recall()

    # Statistics after
    tokens_after = count_tokens_estimate(optimized_messages)
    nodes_after = len([n for n in memory.graph.nodes.values() if n.active is True])

    print(f"\n✅ Optimization Complete!")
    print(f"\n📊 Statistics After Optimization:")
    print(f"   - Optimized messages: {len(optimized_messages)}")
    print(f"   - Estimated tokens: ~{tokens_after}")
    print(f"   - Active nodes: {nodes_after}")
    print(f"   - Token reduction: {((tokens_before - tokens_after) / tokens_before * 100):.1f}%")

    # Show optimized graph
    print("\n" + "-" * 70)
    print("GRAPH AFTER OPTIMIZATION")
    print("-" * 70)
    print(memory.graph.pretty_print(mode="simple"))

    # Show node details
    print("\n" + "-" * 70)
    print("NODE DETAILS")
    print("-" * 70)

    for node_id, node in memory.graph.nodes.items():
        status = "Active" if node.active is True else ("Flushed" if node.active == "Flushed" else "Inactive")
        print(f"\nNode {node_id} [{node.kind}] [{status}]")
        if node.kind == "summary":
            try:
                notes = json.loads(node.thought) if isinstance(node.thought, str) else node.thought
                if notes and len(notes) > 0:
                    content = notes[0].get("content", "")[:100]
                    print(f"   Summary: {content}...")
            except:
                print(f"   Thought: {str(node.thought)[:100]}...")

    # Save for analysis
    save_path = os.path.join(os.path.dirname(__file__), "complex_scenario_memory.json")
    memory.save_memory(save_path)
    print(f"\n💾 Memory saved to: {save_path}")

    # Final summary
    print("\n" + "=" * 70)
    print("  TEST COMPLETED")
    print("=" * 70)
    print(f"""
    📈 Results Summary:
    ───────────────────
    Original episodes:     {len(episodes)}
    Original messages:     {total_messages}
    Original tokens:       ~{tokens_before}

    After optimization:
    Optimized messages:    {len(optimized_messages)}
    Optimized tokens:      ~{tokens_after}
    Token savings:         ~{tokens_before - tokens_after} ({((tokens_before - tokens_after) / tokens_before * 100):.1f}%)

    Graph transformation:
    Nodes before:          {nodes_before}
    Active nodes after:    {nodes_after}
    Summary nodes created: {len([n for n in memory.graph.nodes.values() if n.kind == 'summary'])}
    """)


if __name__ == "__main__":
    asyncio.run(run_complex_scenario())
