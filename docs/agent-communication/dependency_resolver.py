#!/usr/bin/env python3
"""
Agent間の依存関係を管理するモジュール
3-2-1-1-0 バックアップ管理システム
"""

import json
from pathlib import Path
from typing import Dict, List, Set


class DependencyResolver:
    """Agent間の依存関係を管理"""

    def __init__(self, dependencies: Dict[str, List[str]]):
        """
        Args:
            dependencies: {agent_id: [required_agent_ids]}の形式
        """
        self.dependencies = dependencies
        self.completed = set()

    def can_start(self, agent: str) -> bool:
        """
        Agentが作業を開始できるか判定

        Args:
            agent: Agent ID

        Returns:
            True if agent can start, False otherwise
        """
        required = self.dependencies.get(agent, [])
        return all(req in self.completed for req in required)

    def mark_completed(self, agent: str):
        """
        Agentの作業完了をマーク

        Args:
            agent: Agent ID
        """
        self.completed.add(agent)

    def get_ready_agents(self) -> List[str]:
        """
        作業開始可能なAgentをリストアップ

        Returns:
            List of agent IDs that can start work
        """
        all_agents = set(self.dependencies.keys())
        not_completed = all_agents - self.completed
        return [agent for agent in not_completed if self.can_start(agent)]

    def get_blocked_agents(self) -> Dict[str, List[str]]:
        """
        ブロックされているAgentとその理由

        Returns:
            {agent_id: [blocking_agent_ids]}
        """
        blocked = {}
        all_agents = set(self.dependencies.keys())
        not_completed = all_agents - self.completed

        for agent in not_completed:
            if not self.can_start(agent):
                required = self.dependencies.get(agent, [])
                blocking = [r for r in required if r not in self.completed]
                blocked[agent] = blocking

        return blocked

    def get_progress(self) -> Dict[str, any]:
        """
        全体の進捗状況を取得

        Returns:
            Progress statistics
        """
        all_agents = set(self.dependencies.keys())
        total = len(all_agents)
        completed = len(self.completed)
        ready = len(self.get_ready_agents())
        blocked = len(self.get_blocked_agents())

        return {
            "total": total,
            "completed": completed,
            "ready": ready,
            "blocked": blocked,
            "completion_rate": (completed / total * 100) if total > 0 else 0,
        }


def load_project_state(state_file: str = "docs/agent-communication/project-state.json") -> dict:
    """
    プロジェクト状態ファイルを読み込む

    Args:
        state_file: Path to state file

    Returns:
        Project state dictionary
    """
    state_path = Path(state_file)
    if state_path.exists():
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_project_state(state: dict, state_file: str = "docs/agent-communication/project-state.json"):
    """
    プロジェクト状態ファイルを保存

    Args:
        state: Project state dictionary
        state_file: Path to state file
    """
    state_path = Path(state_file)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def update_agent_status(
    agent_id: str,
    status: str,
    current_task: str = None,
    progress: int = 0,
    state_file: str = "docs/agent-communication/project-state.json",
):
    """
    Agent状態を更新

    Args:
        agent_id: Agent ID
        status: Status (idle/working/completed/blocked)
        current_task: Current task description
        progress: Progress percentage (0-100)
        state_file: Path to state file
    """
    from datetime import datetime

    state = load_project_state(state_file)

    if "agents" not in state:
        state["agents"] = {}

    if agent_id not in state["agents"]:
        state["agents"][agent_id] = {}

    state["agents"][agent_id].update(
        {
            "status": status,
            "current_task": current_task,
            "progress": progress,
            "last_update": datetime.utcnow().isoformat() + "Z",
        }
    )

    state["updated_at"] = datetime.utcnow().isoformat() + "Z"

    save_project_state(state, state_file)


if __name__ == "__main__":
    # テスト
    dependencies = {
        "agent-3-api": ["agent-2-database"],
        "agent-5-security": ["agent-2-database", "agent-3-api"],
        "agent-6-logic": ["agent-2-database"],
        "agent-7-scheduler": ["agent-6-logic"],
        "agent-9-test": ["agent-2-database"],
    }

    resolver = DependencyResolver(dependencies)

    print("初期状態:")
    print(f"作業可能: {resolver.get_ready_agents()}")
    print(f"ブロック中: {resolver.get_blocked_agents()}")
    print(f"進捗: {resolver.get_progress()}")

    # Agent-2完了
    resolver.mark_completed("agent-2-database")
    print("\nAgent-2-database完了後:")
    print(f"作業可能: {resolver.get_ready_agents()}")
    print(f"ブロック中: {resolver.get_blocked_agents()}")
    print(f"進捗: {resolver.get_progress()}")
