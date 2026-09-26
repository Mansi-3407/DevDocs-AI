# Interface stub added by Person 4 — do not implement logic here.
# TODO: implement (Person 3)
from app.models import AgentContext, AgentResult


def run(context: AgentContext) -> AgentResult:
    return AgentResult(
        agent_name="tutorial_agent",
        status="skipped",
        summary="Not yet implemented (Person 3).",
        output_files=[],
        issues=[],
        raw_output={},
    )
