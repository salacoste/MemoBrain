"""
MemoBrain with Anthropic SDK support
Modified to work with Anthropic-compatible APIs (e.g., z.ai)
"""

from anthropic import AsyncAnthropic
from typing import List, Dict, Any
import json
import asyncio
import os
import sys

# Handle both package and direct imports
try:
    from .prompts import MEMORY_SYS_PROMPT, FLUSH_AND_FOLD_PROMPT
    from .problem_tree import ReasoningGraph
except ImportError:
    # Direct import when running as script
    from prompts import MEMORY_SYS_PROMPT, FLUSH_AND_FOLD_PROMPT
    from problem_tree import ReasoningGraph


class MemoBrainAnthropic:
    """
    MemoBrain implementation using Anthropic SDK.
    Compatible with z.ai and other Anthropic-format APIs.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_name: str,
    ):
        self.graph = ReasoningGraph()
        self.messages = []
        self.model_name = model_name

        self.agent = AsyncAnthropic(
            api_key=api_key,
            base_url=base_url
        )

    def init_memory(self, task):
        """Initialize memory with a task description"""
        self.graph.add_node(
            kind="task",
            thought=f"Begin to solve the task: {task}",
            related_turn_ids=[0, 1]
        )

    async def memorize(self, new_messages: List[Dict]):
        """Store new reasoning episodes in memory"""
        start_idx = len(self.messages)
        self.messages.extend(new_messages)

        grouped = self._group_pairs(start_idx)
        print(f"{len(grouped)} pairs to memorize...")
        for pair in grouped:
            patch_json = await self._generate_patch(pair)
            try:
                self.graph.apply_patch(patch_json, [start_idx, start_idx + 1])
            except Exception as e:
                print(f"apply patch failed: {e}, continue...")
                continue
            start_idx += 2

    def _group_pairs(self, start_idx: int):
        """Group messages into pairs for processing"""
        grouped = []
        temp = []
        for msg in self.messages[start_idx:]:
            if msg["role"] in ("user", "assistant"):
                temp.append(msg)
                if len(temp) == 2:
                    grouped.append(temp)
                    temp = []
        return grouped

    async def _generate_patch(self, pair):
        """Generate a memory patch from a message pair"""
        round_info = json.dumps(pair, ensure_ascii=False)
        graph_str = self.graph.pretty_print()

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
                    print(f"generate patch failed: {e}, retry in 3 seconds ({attempt + 1}/{max_retries})...")
                    await asyncio.sleep(3)
                else:
                    print("generate patch failed, raise exception.")
                    raise

        try:
            patch_json = json.loads(response)
        except Exception as e:
            print("JSON decode error:", e)
            print("Raw content:", response)
            raise e
        return patch_json

    async def _create_completion(self, system_prompt: str, user_message: str) -> str:
        """Create a completion using Anthropic API"""
        response = await self.agent.messages.create(
            model=self.model_name,
            max_tokens=8 * 1024,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )

        # Extract text from Anthropic response format
        content = response.content[0].text

        # Strip markdown code blocks if present (GLM sometimes wraps JSON)
        content = self._strip_markdown_json(content)
        return content

    def _strip_markdown_json(self, text: str) -> str:
        """Remove markdown code block wrappers from JSON response"""
        text = text.strip()
        # Handle ```json ... ``` format
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    async def recall(self):
        """Optimize memory through flush and fold operations"""
        graph_str = self.graph.pretty_print()

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
                    print(f"recall failed: {e}, retry in 3 seconds ({attempt + 1}/{max_retries})...")
                    await asyncio.sleep(3)
                else:
                    print("recall failed, raise exception.")
                    raise

        try:
            result = json.loads(response)
        except Exception as e:
            print("Error parsing recall response as JSON:", e)
            print("Raw recall response:", response)
            raise e

        for flush_op in result.get("flush_ops", []):
            self.graph.flush_node(flush_op["id"])

        for fold_op in result.get("fold_ops", []):
            self.graph.fold_nodes(
                fold_op["ids"],
                json.dumps(fold_op["notes"]),
                fold_op.get("rationale", "")
            )

        return self._organize()

    def _organize(self):
        """Reorganize messages after optimization"""
        ops_list = []
        active_ids = []
        summary_dict = {}
        total_messages = len(self.messages)
        protected_indices = set()
        protected_indices.update(range(min(3, total_messages)))
        if total_messages > 3:
            protected_indices.update(range(max(3, total_messages - 4), total_messages))

        for node in self.graph.nodes.values():
            is_active = True if node.active is True else False
            kind = node.kind
            related_turn_ids = node.related_turn_ids
            thought = node.thought

            if kind == "summary":
                if related_turn_ids:
                    last_tid = max(related_turn_ids)
                    summary_dict[last_tid] = json.loads(thought) if isinstance(thought, str) else thought
            elif not is_active:
                if isinstance(thought, str):
                    try:
                        t = json.loads(thought)
                    except:
                        t = []
                else:
                    t = thought
                for idx, tid in enumerate(related_turn_ids):
                    if t and len(t) > idx:
                        ops_list.append({"turn_id": tid, "new_message": t[idx]})
            elif is_active and kind:
                for tid in related_turn_ids:
                    active_ids.append(tid)

        summary_turn_ids_to_remove = set()
        for node in self.graph.nodes.values():
            if node.kind == "summary":
                for tid in node.related_turn_ids:
                    if tid not in protected_indices:
                        summary_turn_ids_to_remove.add(tid)

        replace_dict = {}
        for change in ops_list:
            tid = change["turn_id"]
            if tid not in active_ids and tid not in protected_indices and tid not in summary_turn_ids_to_remove:
                replace_dict[tid] = change["new_message"]

        result_messages = []

        for idx, original_msg in enumerate(self.messages):
            if idx in summary_dict and idx not in protected_indices:
                summary_msgs = summary_dict[idx]
                result_messages.extend(summary_msgs)

            if idx in summary_turn_ids_to_remove:
                continue

            if idx in replace_dict:
                result_messages.append(replace_dict[idx])
            else:
                result_messages.append(original_msg)

        return result_messages

    def save_memory(self, file_path: str):
        """Save memory graph to file"""
        graph_dict = self.graph.to_dict()
        with open(file_path, "w") as f:
            json.dump(graph_dict, f, ensure_ascii=False, indent=4)

    def load_memory(self, file_path: str):
        """Load memory graph from file"""
        with open(file_path, "r") as f:
            json_dict = json.load(f)
        self.graph = ReasoningGraph.from_dict(json_dict)

    def load_dict_memory(self, graph_dict: Dict):
        """Load memory graph from dictionary"""
        self.graph = ReasoningGraph.from_dict(graph_dict)
