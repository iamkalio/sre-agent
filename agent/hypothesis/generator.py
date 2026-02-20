"""Hypothesis generator — LLM produces ranked hypotheses from problem frame + context."""

from __future__ import annotations

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel

from agent.framing.models import ProblemFrame
from agent.hypothesis.models import Hypothesis

logger = logging.getLogger("agent.hypothesis")

_SYSTEM_PROMPT = """\
You are an expert SRE investigator. Given a problem frame and enriched context, generate \
a ranked list of root-cause hypotheses. For each hypothesis, include concrete queries \
to test it.

Available tools:
- prometheus: PromQL queries against Prometheus (metrics)
- loki: LogQL queries against Loki (logs)
- tempo: TraceQL search against Tempo (traces)

Respond ONLY with a JSON array of hypotheses:
[
  {
    "id": "h1",
    "title": "short title",
    "description": "detailed explanation of why this could be the cause",
    "likelihood": 0.8,
    "queries": [
      {"tool": "prometheus", "query": "rate(app_errors_total[5m])", "purpose": "check error rate trend"},
      {"tool": "loki", "query": "{service_name=\\"sre-playground\\"} |= \\"error\\"", "purpose": "find error messages"}
    ]
  }
]

Order by likelihood (highest first). Generate 2-5 hypotheses.
"""


async def generate_hypotheses(
    llm: BaseChatModel,
    frame: ProblemFrame,
    context: dict,
) -> list[Hypothesis]:
    """Generate ranked hypotheses from the problem frame and context."""
    user_content = (
        f"Problem frame:\n{frame.model_dump_json(indent=2)}\n\n"
        f"Alert details:\n{json.dumps(context.get('alert', {}), default=str)}\n\n"
        f"Runbook context:\n{chr(10).join(context.get('runbook_context', []))}\n\n"
        f"Signal correlation:\n{json.dumps(context.get('correlation', {}), default=str)}"
    )

    response = await llm.ainvoke([
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ])

    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    parsed = json.loads(raw)
    hypotheses = [Hypothesis.model_validate(h) for h in parsed]
    hypotheses.sort(key=lambda h: h.likelihood, reverse=True)

    logger.info("Generated %d hypotheses for: %s", len(hypotheses), frame.title)
    return hypotheses
