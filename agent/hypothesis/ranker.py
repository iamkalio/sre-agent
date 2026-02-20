"""Hypothesis ranker — re-rank hypotheses after new evidence is gathered."""

from __future__ import annotations

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel

from agent.hypothesis.models import Hypothesis, HypothesisStatus

logger = logging.getLogger("agent.hypothesis")

_SYSTEM_PROMPT = """\
You are an SRE investigator evaluating hypotheses against gathered evidence.

For each hypothesis, decide:
1. Update its likelihood (0.0-1.0) based on new evidence
2. Set status to: confirmed, rejected, or inconclusive
3. Note supporting and contradicting evidence
4. Provide a brief verdict

Respond with a JSON array matching the input structure, with updated fields.
"""


async def rerank_hypotheses(
    llm: BaseChatModel,
    hypotheses: list[Hypothesis],
    evidence: list[dict],
) -> list[Hypothesis]:
    """Re-evaluate hypotheses in light of new evidence."""
    user_content = (
        f"Hypotheses:\n{json.dumps([h.model_dump() for h in hypotheses], indent=2)}\n\n"
        f"New evidence:\n{json.dumps(evidence, indent=2, default=str)}"
    )

    response = await llm.ainvoke([
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ])

    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    updated = [Hypothesis.model_validate(h) for h in json.loads(raw)]
    updated.sort(key=lambda h: h.likelihood, reverse=True)

    confirmed = [h for h in updated if h.status == HypothesisStatus.CONFIRMED]
    if confirmed:
        logger.info("Hypothesis confirmed: %s", confirmed[0].title)

    return updated
