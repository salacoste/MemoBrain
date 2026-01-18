"""
Collaborative Memory System
Multi-participant memory where different agents/users contribute evidence.
NO automatic optimization - pure knowledge accumulation.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import uuid


@dataclass
class MemoryNode:
    """A node in the collaborative memory graph"""
    node_id: str
    kind: str  # "task", "subtask", "evidence", "insight"
    content: str
    participant: str  # Who contributed this node
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "kind": self.kind,
            "content": self.content,
            "participant": self.participant,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "tags": self.tags
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryNode":
        return cls(
            node_id=data["node_id"],
            kind=data["kind"],
            content=data["content"],
            participant=data["participant"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", [])
        )


@dataclass
class MemoryEdge:
    """A relationship between nodes"""
    edge_id: str
    source_id: str
    target_id: str
    relation: str  # "supports", "contradicts", "extends", "refines", "questions"
    created_by: str  # Participant who created this edge
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation": self.relation,
            "created_by": self.created_by,
            "rationale": self.rationale
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEdge":
        return cls(
            edge_id=data["edge_id"],
            source_id=data["source_id"],
            target_id=data["target_id"],
            relation=data["relation"],
            created_by=data["created_by"],
            rationale=data.get("rationale", "")
        )


class CollaborativeMemory:
    """
    Multi-participant collaborative memory system.

    Features:
    - Multiple participants can add evidence
    - Track who contributed what
    - Query by participant, tags, or content
    - NO automatic optimization (pure accumulation)
    - Export for analysis
    """

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.nodes: Dict[str, MemoryNode] = {}
        self.edges: List[MemoryEdge] = []
        self.participants: Dict[str, Dict[str, Any]] = {}  # participant metadata
        self._node_counter = 0

    def register_participant(
        self,
        participant_id: str,
        role: str = "agent",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Register a participant (agent or user)"""
        self.participants[participant_id] = {
            "role": role,
            "registered_at": datetime.now().isoformat(),
            "contributions": 0,
            **(metadata or {})
        }

    def add_task(
        self,
        content: str,
        participant: str = "system",
        tags: Optional[List[str]] = None
    ) -> str:
        """Add a main task node"""
        return self._add_node(
            kind="task",
            content=content,
            participant=participant,
            tags=tags or ["task"]
        )

    def add_evidence(
        self,
        content: str,
        participant: str,
        parent_id: Optional[str] = None,
        relation: str = "supports",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add evidence from a participant"""
        node_id = self._add_node(
            kind="evidence",
            content=content,
            participant=participant,
            tags=tags or [],
            metadata=metadata or {}
        )

        # Link to parent if specified
        if parent_id:
            self.add_edge(
                source_id=node_id,
                target_id=parent_id,
                relation=relation,
                created_by=participant
            )

        return node_id

    def add_insight(
        self,
        content: str,
        participant: str,
        based_on: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """Add an insight/conclusion derived from evidence"""
        node_id = self._add_node(
            kind="insight",
            content=content,
            participant=participant,
            tags=tags or ["insight"]
        )

        # Link to source nodes
        if based_on:
            for source_id in based_on:
                self.add_edge(
                    source_id=node_id,
                    target_id=source_id,
                    relation="derived_from",
                    created_by=participant
                )

        return node_id

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relation: str,
        created_by: str,
        rationale: str = ""
    ) -> str:
        """Add a relationship between nodes"""
        edge_id = f"e_{len(self.edges) + 1}"
        edge = MemoryEdge(
            edge_id=edge_id,
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            created_by=created_by,
            rationale=rationale
        )
        self.edges.append(edge)
        return edge_id

    def _add_node(
        self,
        kind: str,
        content: str,
        participant: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Internal: add a node to the graph"""
        self._node_counter += 1
        node_id = f"n_{self._node_counter}"

        node = MemoryNode(
            node_id=node_id,
            kind=kind,
            content=content,
            participant=participant,
            tags=tags or [],
            metadata=metadata or {}
        )

        self.nodes[node_id] = node

        # Update participant stats
        if participant in self.participants:
            self.participants[participant]["contributions"] += 1

        return node_id

    # Query methods
    def get_by_participant(self, participant: str) -> List[MemoryNode]:
        """Get all nodes from a specific participant"""
        return [n for n in self.nodes.values() if n.participant == participant]

    def get_by_kind(self, kind: str) -> List[MemoryNode]:
        """Get all nodes of a specific kind"""
        return [n for n in self.nodes.values() if n.kind == kind]

    def get_by_tag(self, tag: str) -> List[MemoryNode]:
        """Get all nodes with a specific tag"""
        return [n for n in self.nodes.values() if tag in n.tags]

    def get_evidence_for_task(self, task_id: str) -> List[MemoryNode]:
        """Get all evidence supporting a task"""
        evidence_ids = set()
        for edge in self.edges:
            if edge.target_id == task_id and edge.relation == "supports":
                evidence_ids.add(edge.source_id)
        return [self.nodes[nid] for nid in evidence_ids if nid in self.nodes]

    def get_children(self, node_id: str) -> List[MemoryNode]:
        """Get all nodes that link TO this node"""
        child_ids = set()
        for edge in self.edges:
            if edge.target_id == node_id:
                child_ids.add(edge.source_id)
        return [self.nodes[nid] for nid in child_ids if nid in self.nodes]

    # Export methods
    def to_dict(self) -> Dict[str, Any]:
        """Export memory to dictionary"""
        return {
            "session_id": self.session_id,
            "participants": self.participants,
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CollaborativeMemory":
        """Load memory from dictionary"""
        memory = cls(session_id=data.get("session_id"))
        memory.participants = data.get("participants", {})
        memory.nodes = {
            nid: MemoryNode.from_dict(nd)
            for nid, nd in data.get("nodes", {}).items()
        }
        memory.edges = [
            MemoryEdge.from_dict(ed)
            for ed in data.get("edges", [])
        ]
        memory._node_counter = len(memory.nodes)
        return memory

    def save(self, file_path: str):
        """Save to JSON file"""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, file_path: str) -> "CollaborativeMemory":
        """Load from JSON file"""
        with open(file_path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def pretty_print(self) -> str:
        """Human-readable graph representation"""
        lines = [
            f"=== Collaborative Memory [{self.session_id}] ===",
            f"Participants: {list(self.participants.keys())}",
            f"Nodes: {len(self.nodes)} | Edges: {len(self.edges)}",
            ""
        ]

        # Group by kind
        tasks = self.get_by_kind("task")
        for task in tasks:
            lines.append(f"📋 [{task.node_id}] TASK ({task.participant})")
            lines.append(f"   {task.content[:80]}...")

            # Get supporting evidence
            evidence = self.get_children(task.node_id)
            for ev in evidence:
                icon = "🔍" if ev.kind == "evidence" else "💡"
                lines.append(f"   └─ {icon} [{ev.node_id}] {ev.kind.upper()} ({ev.participant})")
                lines.append(f"      {ev.content[:60]}...")

        # Show insights
        insights = self.get_by_kind("insight")
        if insights:
            lines.append("\n💡 INSIGHTS:")
            for ins in insights:
                lines.append(f"   [{ins.node_id}] ({ins.participant}): {ins.content[:60]}...")

        return "\n".join(lines)

    def summary_by_participant(self) -> Dict[str, Dict[str, int]]:
        """Get contribution summary by participant"""
        summary = {}
        for p_id in self.participants:
            nodes = self.get_by_participant(p_id)
            summary[p_id] = {
                "total": len(nodes),
                "evidence": len([n for n in nodes if n.kind == "evidence"]),
                "insights": len([n for n in nodes if n.kind == "insight"]),
                "tasks": len([n for n in nodes if n.kind == "task"])
            }
        return summary
