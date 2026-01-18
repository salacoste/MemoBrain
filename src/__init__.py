"""
MemoBrain - Executive Memory System for AI Agents

Components:
- memobrain: Original OpenAI-compatible interface
- memobrain_anthropic: Anthropic SDK adapter (for z.ai)
- memobrain_temporal: Temporal knowledge tracking extension
- mcp_server: MCP server for Claude Code integration
"""

from .memobrain import MemoBrain

# Extended components (may not be available if dependencies missing)
try:
    from .memobrain_anthropic import MemoBrainAnthropic
except ImportError:
    MemoBrainAnthropic = None

try:
    from .memobrain_temporal import TemporalMemoBrain
    from .problem_tree_temporal import TemporalReasoningGraph, TemporalReasoningNode
except ImportError:
    TemporalMemoBrain = None
    TemporalReasoningGraph = None
    TemporalReasoningNode = None

__all__ = [
    "MemoBrain",
    "MemoBrainAnthropic",
    "TemporalMemoBrain",
    "TemporalReasoningGraph",
    "TemporalReasoningNode",
]

__version__ = "1.0.0"
