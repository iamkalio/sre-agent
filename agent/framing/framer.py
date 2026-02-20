"""Problem framer — uses LLM to produce a structured ProblemFrame from alert context."""

from __future__ import annotations

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel

from agent.framing.models import ProblemFrame

logger = logging.getLogger("agent.framing")

_SYSTEM_PROMPT = """\
You are an expert Site Reliability Engineer. Given an alert and its surrounding context \
(metrics snapshot, error logs, traces, runbook excerpts, past incidents), produce a \
structured problem frame.

Respond ONLY with valid JSON matching this schema:
{
  "title": "short descriptive title",
  "what": "what is happening",
  "when": "when it started and current duration",
  "where": "which services/components are affected",
  "impact": "none | low | medium | high | critical",
  "affected_components": ["list", "of", "components"],
  "initial_observations": ["observation 1", "observation 2"],
  "investigation_scope": "what the investigation should focus on",
  "questions_to_answer": ["question 1", "question 2"]
}
"""


async def frame_problem(llm: BaseChatModel, context: dict) -> ProblemFrame:
    """Ask the LLM to produce a ProblemFrame from enriched alert context."""
    user_content = (
        f"Alert: {json.dumps(context['alert'], default=str)}\n\n"
        f"Runbook context:\n{chr(10).join(context.get('runbook_context', []))}\n\n"
        f"Past incidents:\n{chr(10).join(context.get('past_incidents', []))}\n\n"
        f"Signal correlation:\n{json.dumps(context.get('correlation', {}), default=str)}"
    )

    response = await llm.ainvoke([
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ])

    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    frame = ProblemFrame.model_validate_json(raw)
    logger.info("Problem framed: %s (impact=%s)", frame.title, frame.impact)
    return frame
