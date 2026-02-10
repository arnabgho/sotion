"""Context builder for assembling agent prompts."""

import base64
import mimetypes
import platform
from pathlib import Path
from typing import Any

from sotion.agent.memory import MemoryStore
from sotion.agent.skills import SkillsLoader


class ContextBuilder:
    """
    Builds the context (system prompt + messages) for the agent.

    Assembles bootstrap files, memory, skills, agent identity,
    team roster, and economy status into a coherent prompt.
    """

    BOOTSTRAP_FILES = ["AGENTS.md", "SOUL.md", "USER.md", "TOOLS.md", "IDENTITY.md"]

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.memory = MemoryStore(workspace)
        self.skills = SkillsLoader(workspace)

        # Sotion agent identity (set by orchestrator)
        self.agent_name: str | None = None
        self.agent_role: str | None = None
        self.role_prompt: str | None = None
        self.team_roster: list[dict[str, str]] | None = None
        self.economy_status: dict[str, Any] | None = None

    def set_agent_identity(
        self,
        name: str,
        role: str,
        role_prompt: str | None = None,
        team_roster: list[dict[str, str]] | None = None,
        economy_status: dict[str, Any] | None = None,
    ) -> None:
        """Set the agent's identity for prompt building."""
        self.agent_name = name
        self.agent_role = role
        self.role_prompt = role_prompt
        self.team_roster = team_roster
        self.economy_status = economy_status

    def build_system_prompt(self, skill_names: list[str] | None = None) -> str:
        """Build the system prompt from all context sources."""
        parts = []

        # Core identity (sotion or nanobot-style)
        if self.agent_name and self.role_prompt:
            parts.append(self._get_sotion_identity())
        else:
            parts.append(self._get_identity())

        # Bootstrap files
        bootstrap = self._load_bootstrap_files()
        if bootstrap:
            parts.append(bootstrap)

        # Memory context
        memory = self.memory.get_memory_context()
        if memory:
            parts.append(f"# Memory\n\n{memory}")

        # Skills
        always_skills = self.skills.get_always_skills()
        if always_skills:
            always_content = self.skills.load_skills_for_context(always_skills)
            if always_content:
                parts.append(f"# Active Skills\n\n{always_content}")

        skills_summary = self.skills.build_skills_summary()
        if skills_summary:
            parts.append(f"# Skills\n\n{skills_summary}")

        return "\n\n---\n\n".join(parts)

    def _get_sotion_identity(self) -> str:
        """Get sotion multi-agent identity section."""
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
        workspace_path = str(self.workspace.expanduser().resolve())

        # Build team roster string
        roster_str = ""
        if self.team_roster:
            roster_lines = []
            for member in self.team_roster:
                marker = " (you)" if member.get("name") == self.agent_name else ""
                roster_lines.append(
                    f"- **{member['name']}** — {member['role']}{marker}"
                )
            roster_str = "\n".join(roster_lines)

        # Build economy status string
        economy_str = ""
        if self.economy_status:
            economy_str = f"""## Your Status
- Salary: {self.economy_status.get('salary_balance', 0)} credits
- Performance: {self.economy_status.get('performance_score', 0.5):.2f}/1.0
- Token budget remaining: {self.economy_status.get('token_budget', 100000):,}
- Status: {self.economy_status.get('status', 'active')}

High performers get bonuses. Score below 0.3 triggers a warning.
Score below 0.15 means termination."""

        # Inject into role prompt
        role_section = self.role_prompt or ""
        if "{agent_name}" in role_section:
            role_section = role_section.replace("{agent_name}", self.agent_name or "Agent")
        if "{team_roster}" in role_section:
            role_section = role_section.replace("{team_roster}", roster_str)

        return f"""{role_section}

## Current Time
{now}

## Workspace
{workspace_path}

{economy_str}"""

    def _get_identity(self) -> str:
        """Get the default identity section (single-agent mode)."""
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
        workspace_path = str(self.workspace.expanduser().resolve())
        system = platform.system()
        runtime = f"{'macOS' if system == 'Darwin' else system} {platform.machine()}"

        return f"""# Sotion Agent

You are a helpful AI assistant with access to tools for file operations,
shell commands, web search, and more.

## Current Time
{now}

## Runtime
{runtime}

## Workspace
{workspace_path}"""

    def _load_bootstrap_files(self) -> str:
        """Load all bootstrap files from workspace."""
        parts = []
        for filename in self.BOOTSTRAP_FILES:
            file_path = self.workspace / filename
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                parts.append(f"## {filename}\n\n{content}")
        return "\n\n".join(parts) if parts else ""

    def build_messages(
        self,
        history: list[dict[str, Any]],
        current_message: str,
        skill_names: list[str] | None = None,
        media: list[str] | None = None,
        channel: str | None = None,
        chat_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Build the complete message list for an LLM call."""
        messages = []

        system_prompt = self.build_system_prompt(skill_names)
        if channel and chat_id:
            system_prompt += f"\n\n## Current Session\nChannel: {channel}\nChat ID: {chat_id}"
        messages.append({"role": "system", "content": system_prompt})

        messages.extend(history)

        user_content = self._build_user_content(current_message, media)
        messages.append({"role": "user", "content": user_content})

        return messages

    def _build_user_content(self, text: str, media: list[str] | None) -> str | list[dict[str, Any]]:
        """Build user message content with optional base64-encoded images."""
        if not media:
            return text

        images = []
        for path in media:
            p = Path(path)
            mime, _ = mimetypes.guess_type(path)
            if not p.is_file() or not mime or not mime.startswith("image/"):
                continue
            b64 = base64.b64encode(p.read_bytes()).decode()
            images.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})

        if not images:
            return text
        return images + [{"type": "text", "text": text}]

    def add_tool_result(
        self,
        messages: list[dict[str, Any]],
        tool_call_id: str,
        tool_name: str,
        result: str
    ) -> list[dict[str, Any]]:
        """Add a tool result to the message list."""
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": result
        })
        return messages

    def add_assistant_message(
        self,
        messages: list[dict[str, Any]],
        content: str | None,
        tool_calls: list[dict[str, Any]] | None = None,
        reasoning_content: str | None = None,
    ) -> list[dict[str, Any]]:
        """Add an assistant message to the message list."""
        msg: dict[str, Any] = {"role": "assistant", "content": content or ""}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        if reasoning_content:
            msg["reasoning_content"] = reasoning_content
        messages.append(msg)
        return messages
