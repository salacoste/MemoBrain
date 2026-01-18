"""
Temporal MemoBrain - Extended with timestamps and knowledge versioning.

Uses TemporalReasoningGraph for knowledge evolution tracking.
Compatible with z.ai Anthropic endpoint.
"""

from anthropic import AsyncAnthropic
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import asyncio

try:
    from .prompts import MEMORY_SYS_PROMPT, FLUSH_AND_FOLD_PROMPT
    from .problem_tree_temporal import (
        TemporalReasoningGraph,
        TemporalReasoningNode,
        convert_from_original,
    )
except ImportError:
    from prompts import MEMORY_SYS_PROMPT, FLUSH_AND_FOLD_PROMPT
    from problem_tree_temporal import (
        TemporalReasoningGraph,
        TemporalReasoningNode,
        convert_from_original,
    )


class TemporalMemoBrain:
    """
    Extended MemoBrain with temporal knowledge management.

    Features:
    - All nodes have timestamps
    - Session-based grouping
    - Knowledge supersedes mechanism
    - Temporal queries
    - Conflict detection
    - Multi-participant support
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_name: str,
        session_id: str = None,
        default_participant: str = "agent",
    ):
        self.graph = TemporalReasoningGraph(session_id=session_id)
        self.messages = []
        self.model_name = model_name
        self.default_participant = default_participant

        self.agent = AsyncAnthropic(
            api_key=api_key,
            base_url=base_url
        )

    # ==================== Core Methods ====================

    def init_memory(self, task: str, tags: List[str] = None):
        """Initialize memory with a task (with timestamp)"""
        self.graph.add_node(
            kind="task",
            thought=f"Begin to solve the task: {task}",
            related_turn_ids=[0, 1],
            tags=tags or ["task"],
            participant="system",
        )

    async def memorize(
        self,
        new_messages: List[Dict],
        tags: List[str] = None,
        participant: str = None,
    ):
        """Store new reasoning episodes with temporal tracking"""
        participant = participant or self.default_participant
        start_idx = len(self.messages)
        self.messages.extend(new_messages)

        grouped = self._group_pairs(start_idx)
        print(f"{len(grouped)} pairs to memorize...")

        for pair in grouped:
            patch_json = await self._generate_patch(pair)
            try:
                self._apply_patch_temporal(
                    patch_json,
                    [start_idx, start_idx + 1],
                    tags=tags,
                    participant=participant,
                )
            except Exception as e:
                print(f"apply patch failed: {e}, continue...")
                continue
            start_idx += 2

    def _apply_patch_temporal(
        self,
        patch_json: Dict[str, Any],
        related_turn_ids: List[int],
        tags: List[str] = None,
        participant: str = "agent",
    ):
        """Apply patch with temporal metadata"""
        tempid2realid = {}

        for node in patch_json.get("add_nodes", []):
            real_node = self.graph.add_node(
                kind=node["kind"],
                thought=node["thought"],
                related_turn_ids=related_turn_ids,
                tags=tags or [],
                participant=participant,
            )
            tempid2realid[node["tmp_id"]] = real_node.node_id

        for edge in patch_json.get("add_edges", []):
            src = str(edge["src"])
            dst = str(edge["dst"])

            if src in tempid2realid:
                src = tempid2realid[src]
            else:
                src = int(src)

            if dst in tempid2realid:
                dst = tempid2realid[dst]
            else:
                dst = int(dst)

            self.graph.add_edge(
                src=src,
                dst=dst,
                rationale=edge.get("rationale", ""),
                created_by=participant,
            )

    def _group_pairs(self, start_idx: int):
        """Group messages into pairs"""
        grouped = []
        temp = []
        for msg in self.messages[start_idx:]:
            if msg["role"] in ("user", "assistant") or msg["role"].startswith("Agent_"):
                temp.append(msg)
                if len(temp) == 2:
                    grouped.append(temp)
                    temp = []
        return grouped

    async def _generate_patch(self, pair):
        """Generate patch from message pair"""
        round_info = json.dumps(pair, ensure_ascii=False)
        graph_str = self.graph.pretty_print(show_timestamps=False)

        current_message = f"CURRENT_INTERACTION:\n{round_info}\n\n{graph_str}"

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self._create_completion(
                    system_prompt=MEMORY_SYS_PROMPT,
                    user_message=current_message
                )
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"generate patch failed: {e}, retry ({attempt + 1}/{max_retries})...")
                    await asyncio.sleep(3)
                else:
                    raise

        try:
            patch_json = json.loads(response)
        except Exception as e:
            print("JSON decode error:", e)
            print("Raw content:", response)
            raise
        return patch_json

    async def _create_completion(self, system_prompt: str, user_message: str) -> str:
        """Create completion using Anthropic API"""
        response = await self.agent.messages.create(
            model=self.model_name,
            max_tokens=8 * 1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )

        content = response.content[0].text
        return self._strip_markdown_json(content)

    def _strip_markdown_json(self, text: str) -> str:
        """Remove markdown code block wrappers"""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    async def recall(self):
        """Optimize memory (same as original)"""
        graph_str = self.graph.pretty_print(show_timestamps=False)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self._create_completion(
                    system_prompt=FLUSH_AND_FOLD_PROMPT,
                    user_message=f"CURRENT_GRAPH:\n{graph_str}"
                )
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"recall failed: {e}, retry ({attempt + 1}/{max_retries})...")
                    await asyncio.sleep(3)
                else:
                    raise

        try:
            result = json.loads(response)
        except Exception as e:
            print("Error parsing recall response:", e)
            raise

        # Note: flush/fold operations would need graph method updates
        # For now, just return organized messages
        return self._organize()

    def _organize(self):
        """Organize messages based on graph state"""
        # Simplified - return all messages for now
        return self.messages.copy()

    # ==================== Temporal Methods ====================

    def add_knowledge(
        self,
        content: str,
        kind: str = "evidence",
        tags: List[str] = None,
        participant: str = None,
        supersedes: List[int] = None,
        link_to: int = None,
    ) -> int:
        """
        Manually add knowledge with full temporal tracking.

        Args:
            content: The knowledge content
            kind: Node kind (evidence, subtask, etc.)
            tags: Topic tags for categorization
            participant: Who is adding this knowledge
            supersedes: List of node IDs this replaces
            link_to: Node ID to link this to (as supporting evidence)

        Returns:
            The new node's ID
        """
        participant = participant or self.default_participant

        node = self.graph.add_node(
            kind=kind,
            thought=content,
            related_turn_ids=[],
            tags=tags or [],
            participant=participant,
            supersedes=supersedes or [],
        )

        if link_to is not None:
            self.graph.add_edge(
                src=node.node_id,
                dst=link_to,
                rationale=f"supports node {link_to}",
                created_by=participant,
            )

        return node.node_id

    def update_knowledge(
        self,
        old_node_id: int,
        new_content: str,
        participant: str = None,
    ) -> int:
        """
        Update knowledge by creating a new node that supersedes the old one.

        Args:
            old_node_id: ID of the node to update
            new_content: New content
            participant: Who is making the update

        Returns:
            The new node's ID
        """
        participant = participant or self.default_participant
        new_node = self.graph.supersede_node(
            old_node_id=old_node_id,
            new_thought=new_content,
            participant=participant,
        )
        return new_node.node_id

    def get_current_knowledge(self, tag: str = None) -> List[TemporalReasoningNode]:
        """Get current (non-superseded) knowledge, optionally filtered by tag"""
        if tag:
            return self.graph.get_by_tag(tag, include_superseded=False)
        return self.graph.get_active_nodes()

    def get_knowledge_history(self, tag: str) -> List[TemporalReasoningNode]:
        """Get full history of knowledge for a tag"""
        return self.graph.get_history_by_tag(tag)

    def get_latest(self, tag: str) -> Optional[TemporalReasoningNode]:
        """Get the most recent knowledge for a tag"""
        return self.graph.get_latest_by_tag(tag)

    def get_state_at(self, timestamp: datetime) -> List[TemporalReasoningNode]:
        """Get knowledge state at a specific point in time"""
        return self.graph.get_state_at(timestamp)

    def find_conflicts(self, tag: str) -> List[List[TemporalReasoningNode]]:
        """Find potential conflicting knowledge for a tag"""
        return self.graph.find_potential_conflicts(tag)

    # ==================== Persistence ====================

    def save_memory(self, file_path: str):
        """Save memory with full temporal data"""
        data = {
            "version": "temporal_v1",
            "saved_at": datetime.now().isoformat(),
            "default_participant": self.default_participant,
            "messages": self.messages,
            "graph": self.graph.to_dict(),
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_memory(self, file_path: str):
        """Load memory from file"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if data.get("version") == "temporal_v1":
            self.messages = data.get("messages", [])
            self.graph = TemporalReasoningGraph.from_dict(data["graph"])
            self.default_participant = data.get("default_participant", "agent")
        else:
            # Legacy format - convert
            self.graph = convert_from_original(data)
            self.messages = []

    # ==================== Visualization ====================

    def show_graph(self, mode: str = "full"):
        """Print the current graph"""
        print(self.graph.pretty_print(mode=mode))

    def show_timeline(self):
        """Print chronological timeline"""
        print(self.graph.timeline())

    def show_stats(self):
        """Print statistics"""
        stats = self.graph.stats()
        print("\n=== Memory Statistics ===")
        print(f"Session: {stats['session_id']}")
        print(f"Age: {stats['age_hours']:.1f} hours")
        print(f"Total nodes: {stats['total_nodes']}")
        print(f"Active nodes: {stats['active_nodes']}")
        print(f"Superseded: {stats['superseded_nodes']}")
        print(f"Edges: {stats['edges']}")
        print(f"By kind: {stats['by_kind']}")
        print(f"By participant: {stats['by_participant']}")
        print(f"Tags: {stats['unique_tags']}")

    # ==================== Session Management ====================

    def start_new_session(self, session_id: str = None):
        """Start a new session (keeps existing nodes but changes session ID)"""
        if session_id:
            self.graph.session_id = session_id
        else:
            self.graph.session_id = self.graph._generate_session_id()
        print(f"New session started: {self.graph.session_id}")

    @property
    def session_id(self) -> str:
        """Get current session ID"""
        return self.graph.session_id
