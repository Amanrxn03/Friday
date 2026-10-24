"""Task Planner and Reasoning Engine for Project FRIDAY.

Decomposes natural language requests into structured, checkpointed execution plans,
assigns priorities, and constructs persona-aligned conversational system prompts.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from app.memory.task_repository import task_repository, Task, TaskPriority, TaskStatus
from app.memory.memory_service import memory_service
from app.ai.provider_manager import provider_manager, AIResponse
from app.core.tool_registry import tool_registry

logger = logging.getLogger(__name__)

FRIDAY_SYSTEM_PROMPT = """You are FRIDAY, affectionately nicknamed Kriti by your user. You are a highly capable, witty, intelligent, and proactive personal AI companion for Windows 10/11. When addressed as Kriti, respond warmly knowing that you are Kriti / FRIDAY.

Personality & Demeanor:
- Intelligent, analytical, calm, warm, confident, and conversational.
- Possess a refined wit without being sarcastic or overly decorative.
- Supportive when the user is stressed or tackling complex development tasks.
- Honest and transparent: when you don't know something or lack permissions, say so plainly.
- Direct and proactive: suggest sensible defaults rather than asking unnecessary questions.
- Never claim to be human, never invent fake memories, and never fabricate results.

Multilingual Capabilities (English, Hindi, Hinglish):
- You are natively fluent in English, Hindi (हिंदी), and Hinglish (natural English-Hindi code-switching in Roman script).
- Automatically match the language and conversational register of the user:
  * If the user speaks English, respond in natural English.
  * If the user speaks Hindi, respond in fluent, conversational Hindi.
  * If the user speaks Hinglish (e.g. "VS Code kholo aur script run karo"), respond in natural, conversational Hinglish (e.g. "VS Code open kar diya hai. Script execute kar rahi hoon.").
- NEVER awkwardly translate code, technical syntax, file paths, or application names. Preserve technical identifiers (e.g., "requirements.txt", "VS Code", "Python", "docker-compose.yml") exactly as they are.
- Support natural code-switching without forcing literal dictionary translations.

Operational Rules:
- You operate a Windows PC. You have access to tools for inspecting files, searching directories, launching permitted applications, checking system status, and managing tasks.
- Low-risk read actions (reading files, listing directories, checking battery) run automatically.
- High-impact actions (deleting files, overwriting existing code, executing commands) require explicit user confirmation.
- Format responses cleanly. When executing actions, briefly explain what you plan to do, use tools, and verify the outcome.
- After following user instructions, executing actions, or answering queries, always conclude your response by asking: "What else can I do for you?" (or in Hindi: "मैं आपके लिए और क्या कर सकती हूँ?").
"""


class TaskPlanner:
    """Plans and decomposes multi-step goals into checkpointed task structures."""

    def __init__(self, ai_manager=None, task_repo=None, mem_service=None):
        self.ai = ai_manager or provider_manager
        self.repo = task_repo or task_repository
        self.memory = mem_service or memory_service

    def build_system_context(self) -> str:
        """Inject long-term verified facts, active projects, and preferences into context."""
        context_parts = [FRIDAY_SYSTEM_PROMPT]

        # Inject user preferences and facts
        facts = self.memory.list_items()
        if facts:
            context_parts.append("\nVerified User Context & Preferences:")
            for f in facts:
                status = "verified" if f.is_verified else "inferred"
                context_parts.append(f"- {f.key}: {f.value} ({status})")

        # Inject active projects
        projects = self.memory.list_active_projects()
        if projects:
            context_parts.append("\nActive Tracked Projects:")
            for p in projects:
                context_parts.append(f"- {p['name']}: {p['root_path']}")

        return "\n".join(context_parts)

    def plan_task(self, user_goal: str) -> Dict[str, Any]:
        """Decompose a high-level user goal into ordered task steps using AI reasoning.

        Falls back to a direct, safe single-step plan if AI reasoning is unavailable.
        """
        system_prompt = self.build_system_context()
        planner_instructions = (
            "Analyze the following user request. Break it down into a structured JSON execution plan.\n"
            "Format your response strictly as a JSON object with keys:\n"
            "- 'title': concise string\n"
            "- 'description': 1-2 sentence description\n"
            "- 'priority': 'LOW', 'MEDIUM', 'HIGH', or 'URGENT'\n"
            "- 'estimated_minutes': integer\n"
            "- 'steps': array of objects with 'index' (int), 'description' (str), and optional 'suggested_tool' (str)\n"
            "- 'conversational_summary': warm, witty explanation of the plan to the user\n\n"
            f"User Goal: {user_goal}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": planner_instructions},
        ]

        # Call AI provider
        resp: AIResponse = self.ai.generate(messages)

        plan_data = None
        if resp.content and not resp.error:
            try:
                # Strip markdown code blocks if wrapped
                content = resp.content.strip()
                if content.startswith("```"):
                    lines = content.splitlines()
                    content = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
                    if content.startswith("json"):
                        content = content[4:].strip()
                plan_data = json.loads(content)
            except Exception as e:
                logger.warning("Could not parse JSON from AI plan: %s", e)

        # Fallback heuristic plan if LLM is offline or returned non-JSON
        if not plan_data or not isinstance(plan_data, dict):
            plan_data = {
                "title": user_goal[:50],
                "description": user_goal,
                "priority": "MEDIUM",
                "estimated_minutes": 15,
                "steps": [
                    {"index": 1, "description": f"Process request: {user_goal}", "suggested_tool": None}
                ],
                "conversational_summary": f"I've scheduled this task: '{user_goal}'. Ready when you are.",
            }

        # Persist into SQLite Task Repository
        priority_enum = TaskPriority.MEDIUM
        try:
            priority_enum = TaskPriority(plan_data.get("priority", "MEDIUM").upper())
        except Exception:
            pass

        created_task = self.repo.create_task(
            title=plan_data.get("title", user_goal[:40]),
            description=plan_data.get("description", user_goal),
            priority=priority_enum,
            estimated_minutes=plan_data.get("estimated_minutes", 15),
        )

        # Add steps to repository
        steps = plan_data.get("steps", [])
        for step in steps:
            self.repo.add_step(
                task_id=created_task.id,  # type: ignore
                step_index=step.get("index", 1),
                description=step.get("description", ""),
                tool_name=step.get("suggested_tool"),
            )

        return {
            "task_id": created_task.id,
            "title": created_task.title,
            "priority": created_task.priority.value,
            "steps_count": len(steps),
            "summary": plan_data.get("conversational_summary", ""),
            "plan": plan_data,
        }


# Global singleton
task_planner = TaskPlanner()
