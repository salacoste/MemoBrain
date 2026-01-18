#!/usr/bin/env python3
"""
MemoBrain MCP Server

MCP server providing executive memory capabilities for AI agents.
Designed for integration with BMad framework workflows.

Tools:
- memory_init: Initialize memory session for a task
- memory_store: Store reasoning episode or knowledge
- memory_recall: Optimize and retrieve memory context
- memory_query: Query specific knowledge by tag
- memory_handoff: Create summary for agent handoff
- memory_save: Persist memory to file
- memory_load: Load memory from file
- memory_status: Get current memory statistics

Usage:
    # Run with stdio (for Claude Code integration)
    python -m mcp_server

    # Or with HTTP transport
    python -m mcp_server --transport http --port 8080
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.session import ServerSession

# Import MemoBrain components
from memobrain_temporal import TemporalMemoBrain


@dataclass
class MemorySession:
    """Represents an active memory session."""
    session_id: str
    task: str
    memory: TemporalMemoBrain
    agent: str
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)


@dataclass
class AppContext:
    """Application context with shared resources."""
    sessions: Dict[str, MemorySession] = field(default_factory=dict)
    active_session_id: Optional[str] = None
    storage_path: Path = field(default_factory=lambda: Path("./_bmad-output/memory"))

    # API configuration
    api_key: str = ""
    base_url: str = ""
    model_name: str = ""


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle."""
    # Initialize context with configuration from environment
    ctx = AppContext(
        api_key=os.environ.get("ZAI_API_KEY", ""),
        base_url=os.environ.get("ZAI_BASE_URL", "https://api.z.ai/api/anthropic"),
        model_name=os.environ.get("ZAI_MODEL", "GLM-4.5-Air"),
    )

    # Ensure storage directory exists
    ctx.storage_path.mkdir(parents=True, exist_ok=True)

    try:
        yield ctx
    finally:
        # Cleanup: save all active sessions
        for session_id, session in ctx.sessions.items():
            try:
                save_path = ctx.storage_path / f"{session_id}.json"
                session.memory.save_memory(str(save_path))
            except Exception as e:
                print(f"Warning: Failed to save session {session_id}: {e}", file=sys.stderr)


# Create MCP server
mcp = FastMCP(
    "MemoBrain",
    lifespan=app_lifespan
)


def get_app_context(ctx: Context) -> AppContext:
    """Extract AppContext from request context."""
    return ctx.request_context.lifespan_context


def get_active_session(app_ctx: AppContext) -> Optional[MemorySession]:
    """Get the currently active session."""
    if app_ctx.active_session_id and app_ctx.active_session_id in app_ctx.sessions:
        return app_ctx.sessions[app_ctx.active_session_id]
    return None


# ============================================================================
# MCP Tools
# ============================================================================

@mcp.tool()
def memory_init(
    task: str,
    agent: str = "default",
    session_id: Optional[str] = None,
    ctx: Context = None
) -> dict:
    """
    Initialize a new memory session for a task.

    Args:
        task: Description of the task/goal to accomplish
        agent: Name of the agent (e.g., 'pm', 'architect', 'dev')
        session_id: Optional custom session ID (auto-generated if not provided)

    Returns:
        dict with session_id, status, and initial graph info

    Example:
        memory_init("Implement user authentication", agent="architect")
    """
    app_ctx = get_app_context(ctx)

    # Generate session ID if not provided
    if not session_id:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = f"{agent}_{timestamp}"

    # Check if session already exists
    if session_id in app_ctx.sessions:
        return {
            "status": "error",
            "message": f"Session '{session_id}' already exists. Use memory_load or choose different ID."
        }

    # Create new TemporalMemoBrain instance
    memory = TemporalMemoBrain(
        api_key=app_ctx.api_key,
        base_url=app_ctx.base_url,
        model_name=app_ctx.model_name
    )

    # Initialize with task
    memory.init_memory(task, session_id=session_id, participant=agent)

    # Create session
    session = MemorySession(
        session_id=session_id,
        task=task,
        memory=memory,
        agent=agent
    )

    # Store and activate session
    app_ctx.sessions[session_id] = session
    app_ctx.active_session_id = session_id

    return {
        "status": "success",
        "session_id": session_id,
        "task": task,
        "agent": agent,
        "nodes": len(memory.graph.nodes),
        "message": f"Memory initialized for '{task[:50]}...'"
    }


@mcp.tool()
async def memory_store(
    content: str,
    kind: str = "evidence",
    tags: Optional[List[str]] = None,
    participant: Optional[str] = None,
    session_id: Optional[str] = None,
    ctx: Context = None
) -> dict:
    """
    Store knowledge or reasoning episode in memory.

    Args:
        content: The content to store (reasoning, decision, evidence)
        kind: Type of node - 'evidence', 'subtask', 'decision', 'insight'
        tags: Optional tags for categorization (e.g., ['architecture', 'decision'])
        participant: Who is storing this (defaults to session agent)
        session_id: Target session (uses active if not specified)

    Returns:
        dict with node_id and status

    Example:
        memory_store(
            "Decided to use JWT for authentication because...",
            kind="decision",
            tags=["auth", "architecture"]
        )
    """
    app_ctx = get_app_context(ctx)

    # Get target session
    target_id = session_id or app_ctx.active_session_id
    if not target_id or target_id not in app_ctx.sessions:
        return {"status": "error", "message": "No active session. Call memory_init first."}

    session = app_ctx.sessions[target_id]
    session.last_activity = datetime.now()

    # Use session agent if participant not specified
    if not participant:
        participant = session.agent

    # Add knowledge to memory
    node_id = session.memory.add_knowledge(
        content=content,
        kind=kind,
        tags=tags or [],
        participant=participant
    )

    return {
        "status": "success",
        "node_id": node_id,
        "session_id": target_id,
        "kind": kind,
        "tags": tags or [],
        "participant": participant,
        "total_nodes": len(session.memory.graph.nodes)
    }


@mcp.tool()
async def memory_recall(
    session_id: Optional[str] = None,
    ctx: Context = None
) -> dict:
    """
    Optimize memory and retrieve compressed context.

    Triggers the Fold operation to compress completed reasoning paths
    into summaries while preserving semantic content.

    Args:
        session_id: Target session (uses active if not specified)

    Returns:
        dict with optimized messages and statistics

    Example:
        memory_recall()  # Optimize active session
    """
    app_ctx = get_app_context(ctx)

    # Get target session
    target_id = session_id or app_ctx.active_session_id
    if not target_id or target_id not in app_ctx.sessions:
        return {"status": "error", "message": "No active session. Call memory_init first."}

    session = app_ctx.sessions[target_id]
    session.last_activity = datetime.now()

    # Get stats before
    nodes_before = len(session.memory.graph.nodes)

    # Perform recall (optimization)
    optimized_messages = await session.memory.recall()

    # Get stats after
    active_nodes = len([n for n in session.memory.graph.nodes.values() if n.active is True])

    return {
        "status": "success",
        "session_id": target_id,
        "messages_count": len(optimized_messages),
        "nodes_before": nodes_before,
        "active_nodes_after": active_nodes,
        "optimized_context": optimized_messages[:5] if optimized_messages else []  # First 5 messages preview
    }


@mcp.tool()
def memory_query(
    tag: Optional[str] = None,
    kind: Optional[str] = None,
    participant: Optional[str] = None,
    include_history: bool = False,
    session_id: Optional[str] = None,
    ctx: Context = None
) -> dict:
    """
    Query specific knowledge from memory.

    Args:
        tag: Filter by tag (e.g., 'architecture', 'decision')
        kind: Filter by node kind ('evidence', 'subtask', 'decision', 'summary')
        participant: Filter by participant/agent
        include_history: Include superseded versions (for temporal analysis)
        session_id: Target session (uses active if not specified)

    Returns:
        dict with matching knowledge nodes

    Example:
        memory_query(tag="architecture")  # Get all architecture-related knowledge
        memory_query(kind="decision", include_history=True)  # Get all decisions with history
    """
    app_ctx = get_app_context(ctx)

    # Get target session
    target_id = session_id or app_ctx.active_session_id
    if not target_id or target_id not in app_ctx.sessions:
        return {"status": "error", "message": "No active session. Call memory_init first."}

    session = app_ctx.sessions[target_id]

    # Get knowledge based on filters
    if include_history and tag:
        nodes = session.memory.get_knowledge_history(tag)
    elif tag:
        nodes = [session.memory.get_latest(tag)] if session.memory.get_latest(tag) else []
    else:
        nodes = session.memory.get_current_knowledge(tag)

    # Apply additional filters
    results = []
    for node in nodes:
        if node is None:
            continue
        if kind and node.kind != kind:
            continue
        if participant and node.participant != participant:
            continue

        # Parse content
        try:
            content = json.loads(node.thought) if isinstance(node.thought, str) else node.thought
        except:
            content = node.thought

        results.append({
            "node_id": node.node_id,
            "kind": node.kind,
            "content": content,
            "tags": node.tags,
            "participant": node.participant,
            "created_at": node.created_at.isoformat(),
            "version": node.version,
            "active": node.active
        })

    return {
        "status": "success",
        "session_id": target_id,
        "count": len(results),
        "filters": {"tag": tag, "kind": kind, "participant": participant},
        "results": results
    }


@mcp.tool()
def memory_handoff(
    target_agent: str,
    focus_tags: Optional[List[str]] = None,
    include_task: bool = True,
    session_id: Optional[str] = None,
    ctx: Context = None
) -> dict:
    """
    Create a handoff summary for transitioning to another agent.

    Generates a compressed context optimized for the target agent,
    including relevant decisions, insights, and current state.

    Args:
        target_agent: Name of the agent receiving the handoff (e.g., 'dev', 'qa')
        focus_tags: Tags to prioritize in the handoff (e.g., ['architecture', 'api'])
        include_task: Include original task description
        session_id: Source session (uses active if not specified)

    Returns:
        dict with handoff context ready for the target agent

    Example:
        memory_handoff("dev", focus_tags=["architecture", "api-design"])
    """
    app_ctx = get_app_context(ctx)

    # Get source session
    target_id = session_id or app_ctx.active_session_id
    if not target_id or target_id not in app_ctx.sessions:
        return {"status": "error", "message": "No active session. Call memory_init first."}

    session = app_ctx.sessions[target_id]

    # Collect handoff content
    handoff = {
        "from_agent": session.agent,
        "to_agent": target_agent,
        "timestamp": datetime.now().isoformat(),
        "session_id": target_id,
    }

    if include_task:
        handoff["original_task"] = session.task

    # Get current knowledge
    current_knowledge = session.memory.get_current_knowledge()

    # Prioritize by focus tags
    prioritized = []
    other = []

    for node in current_knowledge:
        if node.active is not True:
            continue

        node_data = {
            "kind": node.kind,
            "participant": node.participant,
            "tags": node.tags,
            "created_at": node.created_at.isoformat(),
        }

        try:
            node_data["content"] = json.loads(node.thought) if isinstance(node.thought, str) else node.thought
        except:
            node_data["content"] = node.thought

        # Check if matches focus tags
        if focus_tags and any(tag in node.tags for tag in focus_tags):
            prioritized.append(node_data)
        else:
            other.append(node_data)

    handoff["priority_knowledge"] = prioritized
    handoff["additional_knowledge"] = other[:10]  # Limit additional to 10
    handoff["total_nodes"] = len(current_knowledge)
    handoff["handoff_summary"] = f"Handoff from {session.agent} to {target_agent} with {len(prioritized)} priority items and {len(other)} additional items."

    return {
        "status": "success",
        **handoff
    }


@mcp.tool()
def memory_save(
    filename: Optional[str] = None,
    session_id: Optional[str] = None,
    ctx: Context = None
) -> dict:
    """
    Persist memory session to file.

    Args:
        filename: Custom filename (defaults to session_id.json)
        session_id: Target session (uses active if not specified)

    Returns:
        dict with save path and status

    Example:
        memory_save()  # Save active session
        memory_save("epic-42-auth.json")  # Save with custom name
    """
    app_ctx = get_app_context(ctx)

    # Get target session
    target_id = session_id or app_ctx.active_session_id
    if not target_id or target_id not in app_ctx.sessions:
        return {"status": "error", "message": "No active session. Call memory_init first."}

    session = app_ctx.sessions[target_id]

    # Determine save path
    if filename:
        save_path = app_ctx.storage_path / filename
    else:
        save_path = app_ctx.storage_path / f"{target_id}.json"

    # Save memory
    session.memory.save_memory(str(save_path))

    return {
        "status": "success",
        "session_id": target_id,
        "path": str(save_path),
        "nodes": len(session.memory.graph.nodes),
        "message": f"Memory saved to {save_path}"
    }


@mcp.tool()
def memory_load(
    filename: str,
    session_id: Optional[str] = None,
    agent: str = "default",
    ctx: Context = None
) -> dict:
    """
    Load memory session from file.

    Args:
        filename: File to load (relative to storage path or absolute)
        session_id: Session ID to use (defaults to filename without extension)
        agent: Agent name for the loaded session

    Returns:
        dict with loaded session info

    Example:
        memory_load("epic-42-auth.json", agent="dev")
    """
    app_ctx = get_app_context(ctx)

    # Determine load path
    if os.path.isabs(filename):
        load_path = Path(filename)
    else:
        load_path = app_ctx.storage_path / filename

    if not load_path.exists():
        return {"status": "error", "message": f"File not found: {load_path}"}

    # Determine session ID
    if not session_id:
        session_id = load_path.stem

    # Create new MemoBrain and load
    memory = TemporalMemoBrain(
        api_key=app_ctx.api_key,
        base_url=app_ctx.base_url,
        model_name=app_ctx.model_name
    )
    memory.load_memory(str(load_path))

    # Get task from loaded memory (first task node)
    task = "Loaded session"
    for node in memory.graph.nodes.values():
        if node.kind == "task":
            try:
                task = node.thought.replace("Begin to solve the task: ", "")
            except:
                pass
            break

    # Create session
    session = MemorySession(
        session_id=session_id,
        task=task,
        memory=memory,
        agent=agent
    )

    # Store and activate
    app_ctx.sessions[session_id] = session
    app_ctx.active_session_id = session_id

    return {
        "status": "success",
        "session_id": session_id,
        "path": str(load_path),
        "agent": agent,
        "task": task,
        "nodes": len(memory.graph.nodes),
        "message": f"Memory loaded from {load_path}"
    }


@mcp.tool()
def memory_status(
    session_id: Optional[str] = None,
    ctx: Context = None
) -> dict:
    """
    Get current memory status and statistics.

    Args:
        session_id: Target session (uses active if not specified, or 'all' for all sessions)

    Returns:
        dict with memory statistics

    Example:
        memory_status()  # Active session stats
        memory_status("all")  # All sessions overview
    """
    app_ctx = get_app_context(ctx)

    if session_id == "all":
        # Return overview of all sessions
        sessions_info = []
        for sid, session in app_ctx.sessions.items():
            active_nodes = len([n for n in session.memory.graph.nodes.values() if n.active is True])
            sessions_info.append({
                "session_id": sid,
                "agent": session.agent,
                "task": session.task[:50] + "..." if len(session.task) > 50 else session.task,
                "nodes": len(session.memory.graph.nodes),
                "active_nodes": active_nodes,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "is_active": sid == app_ctx.active_session_id
            })

        return {
            "status": "success",
            "total_sessions": len(sessions_info),
            "active_session": app_ctx.active_session_id,
            "sessions": sessions_info
        }

    # Get specific session
    target_id = session_id or app_ctx.active_session_id
    if not target_id or target_id not in app_ctx.sessions:
        return {"status": "error", "message": "No active session. Call memory_init first."}

    session = app_ctx.sessions[target_id]

    # Collect statistics
    nodes = session.memory.graph.nodes
    edges = session.memory.graph.edges

    # Count by kind
    by_kind = {}
    by_participant = {}
    all_tags = set()

    for node in nodes.values():
        by_kind[node.kind] = by_kind.get(node.kind, 0) + 1
        by_participant[node.participant] = by_participant.get(node.participant, 0) + 1
        all_tags.update(node.tags)

    active_nodes = len([n for n in nodes.values() if n.active is True])

    return {
        "status": "success",
        "session_id": target_id,
        "agent": session.agent,
        "task": session.task,
        "created_at": session.created_at.isoformat(),
        "last_activity": session.last_activity.isoformat(),
        "statistics": {
            "total_nodes": len(nodes),
            "active_nodes": active_nodes,
            "edges": len(edges),
            "by_kind": by_kind,
            "by_participant": by_participant,
            "tags": list(all_tags)
        }
    }


@mcp.tool()
def memory_switch(
    session_id: str,
    ctx: Context = None
) -> dict:
    """
    Switch active session.

    Args:
        session_id: Session to activate

    Returns:
        dict with new active session info

    Example:
        memory_switch("architect_20240115")
    """
    app_ctx = get_app_context(ctx)

    if session_id not in app_ctx.sessions:
        available = list(app_ctx.sessions.keys())
        return {
            "status": "error",
            "message": f"Session '{session_id}' not found.",
            "available_sessions": available
        }

    app_ctx.active_session_id = session_id
    session = app_ctx.sessions[session_id]

    return {
        "status": "success",
        "session_id": session_id,
        "agent": session.agent,
        "task": session.task,
        "nodes": len(session.memory.graph.nodes),
        "message": f"Switched to session '{session_id}'"
    }


# ============================================================================
# Entry point
# ============================================================================

def main():
    """Run the MCP server."""
    import argparse

    parser = argparse.ArgumentParser(description="MemoBrain MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio",
                       help="Transport type (default: stdio)")
    parser.add_argument("--port", type=int, default=8080,
                       help="Port for HTTP transport (default: 8080)")
    args = parser.parse_args()

    if args.transport == "http":
        mcp.run(transport="streamable-http", port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
