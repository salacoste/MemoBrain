"""
Temporal Reasoning Graph - Extended with timestamps and versioning support.

Extends the original ReasoningGraph with:
- Timestamps for all nodes
- Session tracking
- Supersedes mechanism for knowledge evolution
- Temporal queries
"""

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Any, Union, Optional
from datetime import datetime
import itertools
import json
import uuid


NodeKind = Literal[
    "task",
    "subtask",
    "evidence",
    "summary"
]


@dataclass
class TemporalReasoningNode:
    """
    Extended ReasoningNode with temporal tracking.

    New fields:
    - created_at: When the node was created (absolute timestamp)
    - session_id: Which session/sprint this belongs to
    - version: Version number for this piece of knowledge
    - supersedes: List of node IDs this node replaces
    - superseded_by: Node ID that replaced this node (if any)
    - tags: Topic tags for categorization
    - participant: Who created this node
    """
    node_id: int
    kind: NodeKind
    thought: str
    related_turn_ids: List[int]
    active: Union[bool, str] = True

    # Temporal fields
    created_at: datetime = field(default_factory=datetime.now)
    session_id: str = ""
    version: int = 1
    supersedes: List[int] = field(default_factory=list)
    superseded_by: Optional[int] = None

    # Metadata
    tags: List[str] = field(default_factory=list)
    participant: str = "system"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "kind": self.kind,
            "thought": self.thought,
            "related_turn_ids": self.related_turn_ids,
            "active": self.active,
            # Temporal
            "created_at": self.created_at.isoformat(),
            "session_id": self.session_id,
            "version": self.version,
            "supersedes": self.supersedes,
            "superseded_by": self.superseded_by,
            # Metadata
            "tags": self.tags,
            "participant": self.participant,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemporalReasoningNode":
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()

        return cls(
            node_id=data["node_id"],
            kind=data["kind"],
            thought=data["thought"],
            related_turn_ids=data.get("related_turn_ids", []),
            active=data.get("active", True),
            created_at=created_at,
            session_id=data.get("session_id", ""),
            version=data.get("version", 1),
            supersedes=data.get("supersedes", []),
            superseded_by=data.get("superseded_by"),
            tags=data.get("tags", []),
            participant=data.get("participant", "system"),
        )

    def is_superseded(self) -> bool:
        """Check if this node has been superseded by another"""
        return self.superseded_by is not None

    def age_days(self) -> float:
        """Get age of this node in days"""
        return (datetime.now() - self.created_at).total_seconds() / 86400


@dataclass
class TemporalEdge:
    """Edge with creation tracking"""
    src: int
    dst: int
    rationale: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "src": self.src,
            "dst": self.dst,
            "rationale": self.rationale,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemporalEdge":
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()

        return cls(
            src=data["src"],
            dst=data["dst"],
            rationale=data.get("rationale", ""),
            created_at=created_at,
            created_by=data.get("created_by", "system"),
        )


class TemporalReasoningGraph:
    """
    Extended ReasoningGraph with temporal features.

    Features:
    - All nodes have timestamps
    - Session tracking for grouping
    - Supersedes mechanism for knowledge evolution
    - Temporal queries (get state at time T)
    - Conflict detection
    """

    def __init__(self, session_id: str = None):
        self.nodes: Dict[int, TemporalReasoningNode] = {}
        self.edges: List[TemporalEdge] = []
        self._id_counter = itertools.count(1)
        self.session_id = session_id or self._generate_session_id()
        self.created_at = datetime.now()

    def _generate_session_id(self) -> str:
        """Generate session ID based on date"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    # ==================== Node Operations ====================

    def add_node(
        self,
        kind: NodeKind,
        thought: str,
        related_turn_ids: List[int] = None,
        tags: List[str] = None,
        participant: str = "system",
        supersedes: List[int] = None,
    ) -> TemporalReasoningNode:
        """Add a new node with temporal tracking"""
        node = TemporalReasoningNode(
            node_id=next(self._id_counter),
            kind=kind,
            thought=thought,
            related_turn_ids=related_turn_ids or [],
            created_at=datetime.now(),
            session_id=self.session_id,
            tags=tags or [],
            participant=participant,
            supersedes=supersedes or [],
        )

        # Mark superseded nodes
        if supersedes:
            for old_id in supersedes:
                if old_id in self.nodes:
                    self.nodes[old_id].superseded_by = node.node_id

        self.nodes[node.node_id] = node
        return node

    def add_edge(
        self,
        src: int,
        dst: int,
        rationale: str = "",
        created_by: str = "system",
    ) -> TemporalEdge:
        """Add edge with creation tracking"""
        if src not in self.nodes or dst not in self.nodes:
            raise ValueError(f"Unknown node id in edge: {src} -> {dst}")

        edge = TemporalEdge(
            src=src,
            dst=dst,
            rationale=rationale,
            created_at=datetime.now(),
            created_by=created_by,
        )
        self.edges.append(edge)
        return edge

    def supersede_node(
        self,
        old_node_id: int,
        new_thought: str,
        participant: str = "system",
    ) -> TemporalReasoningNode:
        """Create a new node that supersedes an existing one"""
        if old_node_id not in self.nodes:
            raise ValueError(f"Node {old_node_id} not found")

        old_node = self.nodes[old_node_id]

        # Create new node with same kind and tags
        new_node = self.add_node(
            kind=old_node.kind,
            thought=new_thought,
            related_turn_ids=[],
            tags=old_node.tags.copy(),
            participant=participant,
            supersedes=[old_node_id],
        )

        # Copy edges from old node to new node
        for edge in self.edges:
            if edge.dst == old_node_id:
                self.add_edge(
                    src=edge.src,
                    dst=new_node.node_id,
                    rationale=f"[superseded] {edge.rationale}",
                    created_by=participant,
                )

        return new_node

    # ==================== Temporal Queries ====================

    def get_active_nodes(self) -> List[TemporalReasoningNode]:
        """Get all active, non-superseded nodes"""
        return [
            n for n in self.nodes.values()
            if n.active is True and not n.is_superseded()
        ]

    def get_state_at(self, timestamp: datetime) -> List[TemporalReasoningNode]:
        """Get the state of knowledge at a specific time"""
        # Nodes created before timestamp
        valid_nodes = [
            n for n in self.nodes.values()
            if n.created_at <= timestamp
        ]

        # Filter out nodes that were superseded before timestamp
        result = []
        for node in valid_nodes:
            if node.superseded_by is not None:
                superseding_node = self.nodes.get(node.superseded_by)
                if superseding_node and superseding_node.created_at <= timestamp:
                    continue  # Was superseded by this time
            result.append(node)

        return result

    def get_by_tag(self, tag: str, include_superseded: bool = False) -> List[TemporalReasoningNode]:
        """Get nodes by tag"""
        nodes = [n for n in self.nodes.values() if tag in n.tags]
        if not include_superseded:
            nodes = [n for n in nodes if not n.is_superseded()]
        return nodes

    def get_by_participant(self, participant: str) -> List[TemporalReasoningNode]:
        """Get nodes created by a specific participant"""
        return [n for n in self.nodes.values() if n.participant == participant]

    def get_by_session(self, session_id: str) -> List[TemporalReasoningNode]:
        """Get nodes from a specific session"""
        return [n for n in self.nodes.values() if n.session_id == session_id]

    def get_latest_by_tag(self, tag: str) -> Optional[TemporalReasoningNode]:
        """Get the most recent non-superseded node with a tag"""
        nodes = self.get_by_tag(tag, include_superseded=False)
        if not nodes:
            return None
        return max(nodes, key=lambda n: n.created_at)

    def get_history_by_tag(self, tag: str) -> List[TemporalReasoningNode]:
        """Get full history of a tag, including superseded nodes, ordered by time"""
        nodes = self.get_by_tag(tag, include_superseded=True)
        return sorted(nodes, key=lambda n: n.created_at)

    # ==================== Conflict Detection ====================

    def find_potential_conflicts(self, tag: str) -> List[List[TemporalReasoningNode]]:
        """
        Find nodes with the same tag that might conflict.
        Returns groups of nodes that may need resolution.
        """
        active_nodes = self.get_by_tag(tag, include_superseded=False)

        # Group by kind
        by_kind: Dict[str, List[TemporalReasoningNode]] = {}
        for node in active_nodes:
            if node.kind not in by_kind:
                by_kind[node.kind] = []
            by_kind[node.kind].append(node)

        # Return groups with more than one node (potential conflicts)
        return [nodes for nodes in by_kind.values() if len(nodes) > 1]

    # ==================== Serialization ====================

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "nodes": {str(nid): n.to_dict() for nid, n in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemporalReasoningGraph":
        g = cls(session_id=data.get("session_id"))

        if "created_at" in data:
            g.created_at = datetime.fromisoformat(data["created_at"])

        g.nodes = {
            int(nid): TemporalReasoningNode.from_dict(nd)
            for nid, nd in data.get("nodes", {}).items()
        }
        g.edges = [TemporalEdge.from_dict(ed) for ed in data.get("edges", [])]

        if g.nodes:
            max_id = max(g.nodes.keys())
            g._id_counter = itertools.count(max_id + 1)

        return g

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    # ==================== Visualization ====================

    def pretty_print(self, mode: str = "full", show_timestamps: bool = True) -> str:
        """Pretty print with temporal information"""
        lines = []

        lines.append(f"=== Temporal Reasoning Graph ===")
        lines.append(f"Session: {self.session_id}")
        lines.append(f"Created: {self.created_at.strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"Nodes: {len(self.nodes)} | Edges: {len(self.edges)}")
        lines.append("")

        # Build children map
        from collections import defaultdict
        children = defaultdict(list)
        in_degrees = {nid: 0 for nid in self.nodes}

        for edge in self.edges:
            if edge.src in self.nodes and edge.dst in self.nodes:
                children[edge.dst].append((edge.src, edge.rationale))
                in_degrees[edge.src] += 1

        # Find roots (nodes with no incoming edges)
        roots = [nid for nid, deg in in_degrees.items() if deg == 0]
        visited = set()

        def format_node(node: TemporalReasoningNode) -> str:
            status = "Active" if node.active is True else str(node.active)
            if node.is_superseded():
                status = f"Superseded→{node.superseded_by}"

            time_str = ""
            if show_timestamps:
                time_str = f" @{node.created_at.strftime('%m-%d %H:%M')}"

            tags_str = ""
            if node.tags:
                tags_str = f" #{','.join(node.tags)}"

            participant_str = ""
            if node.participant != "system":
                participant_str = f" by:{node.participant}"

            return f"[{node.kind}] [{status}]{time_str}{tags_str}{participant_str}"

        def walk(node_id: int, indent: str):
            if node_id in visited:
                return
            visited.add(node_id)

            node = self.nodes[node_id]
            node_info = format_node(node)

            if mode == "full":
                thought_preview = str(node.thought)[:60]
                if len(str(node.thought)) > 60:
                    thought_preview += "..."
                lines.append(f"{indent}Node {node_id}: {node_info}")
                lines.append(f"{indent}  └ {thought_preview}")
            else:
                lines.append(f"{indent}Node {node_id}: {node_info}")

            for child_id, rationale in children.get(node_id, []):
                if child_id not in visited:
                    lines.append(f"{indent}  ├─→ Node {child_id}")
                    walk(child_id, indent + "  │   ")

        if not roots:
            lines.append("(Empty or circular graph)")
        else:
            for root in sorted(roots):
                walk(root, "")
                lines.append("")

        return "\n".join(lines)

    def timeline(self) -> str:
        """Show nodes in chronological order"""
        lines = ["=== Timeline ===", ""]

        sorted_nodes = sorted(self.nodes.values(), key=lambda n: n.created_at)

        current_date = None
        for node in sorted_nodes:
            node_date = node.created_at.strftime("%Y-%m-%d")
            if node_date != current_date:
                current_date = node_date
                lines.append(f"\n📅 {current_date}")
                lines.append("-" * 40)

            time_str = node.created_at.strftime("%H:%M:%S")
            status = "✓" if node.active is True and not node.is_superseded() else "✗"
            superseded = f" (→{node.superseded_by})" if node.is_superseded() else ""

            lines.append(
                f"  {time_str} {status} Node {node.node_id} [{node.kind}]{superseded}"
            )
            if node.tags:
                lines.append(f"           Tags: {', '.join(node.tags)}")

        return "\n".join(lines)

    # ==================== Statistics ====================

    def stats(self) -> Dict[str, Any]:
        """Get statistics about the graph"""
        active_nodes = self.get_active_nodes()
        superseded = [n for n in self.nodes.values() if n.is_superseded()]

        by_kind = {}
        for node in self.nodes.values():
            by_kind[node.kind] = by_kind.get(node.kind, 0) + 1

        by_participant = {}
        for node in self.nodes.values():
            by_participant[node.participant] = by_participant.get(node.participant, 0) + 1

        all_tags = set()
        for node in self.nodes.values():
            all_tags.update(node.tags)

        return {
            "total_nodes": len(self.nodes),
            "active_nodes": len(active_nodes),
            "superseded_nodes": len(superseded),
            "edges": len(self.edges),
            "by_kind": by_kind,
            "by_participant": by_participant,
            "unique_tags": list(all_tags),
            "session_id": self.session_id,
            "age_hours": (datetime.now() - self.created_at).total_seconds() / 3600,
        }


# ==================== Compatibility Layer ====================

def convert_from_original(original_graph_dict: Dict[str, Any]) -> TemporalReasoningGraph:
    """Convert original ReasoningGraph format to TemporalReasoningGraph"""
    temporal = TemporalReasoningGraph()

    for nid_str, node_data in original_graph_dict.get("nodes", {}).items():
        # Add missing temporal fields
        node_data.setdefault("created_at", datetime.now().isoformat())
        node_data.setdefault("session_id", temporal.session_id)
        node_data.setdefault("version", 1)
        node_data.setdefault("supersedes", [])
        node_data.setdefault("superseded_by", None)
        node_data.setdefault("tags", [])
        node_data.setdefault("participant", "system")

        temporal.nodes[int(nid_str)] = TemporalReasoningNode.from_dict(node_data)

    for edge_data in original_graph_dict.get("edges", []):
        edge_data.setdefault("created_at", datetime.now().isoformat())
        edge_data.setdefault("created_by", "system")
        temporal.edges.append(TemporalEdge.from_dict(edge_data))

    if temporal.nodes:
        max_id = max(temporal.nodes.keys())
        temporal._id_counter = itertools.count(max_id + 1)

    return temporal
