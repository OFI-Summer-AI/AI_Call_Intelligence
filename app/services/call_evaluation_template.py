"""
Sales discovery checklist: each item is scored against the **raw evidence**
transcript (timestamped) in the LLM prompt. Edit to match your playbook.

IDs are stable for dashboards and automation.
"""

from __future__ import annotations

from typing import Any, Dict, List

DISCOVERY_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "problem",
        "category": "discovery",
        "title": "What is the problem?",
        "eval_prompt": "Was the client's core problem, pain, or desired outcome clearly stated?",
    },
    {
        "id": "solution_needed",
        "category": "solution",
        "title": "What type of solution is needed?",
        "eval_prompt": "Was the required solution shape, scope, or capability discussed beyond vague interest?",
    },
    {
        "id": "current_process",
        "category": "discovery",
        "title": "What is the current process?",
        "eval_prompt": "Was the as-is workflow, tools, or operational reality described?",
    },
    {
        "id": "timeline_eta",
        "category": "commercial",
        "title": "What is the target timeline / ETA?",
        "eval_prompt": "Were dates, milestones, or evaluation windows captured with enough specificity to plan?",
    },
    {
        "id": "budget",
        "category": "commercial",
        "title": "What is the budget?",
        "eval_prompt": "Was budget, pricing envelope, approval path, or commercial constraints discussed?",
    },
    {
        "id": "systems_platforms",
        "category": "technical",
        "title": "What systems / platforms are involved?",
        "eval_prompt": "Were systems, integrations, vendors, or data platforms identified?",
    },
    {
        "id": "decision_owner",
        "category": "process",
        "title": "Who owns the decision?",
        "eval_prompt": "Were decision makers, economic buyer, or procurement/security stakeholders identified?",
    },
    {
        "id": "next_steps",
        "category": "close",
        "title": "What are the next steps?",
        "eval_prompt": "Were concrete follow-ups, owners, and time expectations agreed (not only 'we'll reconnect')?",
    },
]


def template_for_prompt() -> List[Dict[str, str]]:
    return [
        {"id": q["id"], "title": q["title"], "eval_prompt": q["eval_prompt"]}
        for q in DISCOVERY_QUESTIONS
    ]
