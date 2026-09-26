# Interface stub added by Person 4 — do not implement logic here.
# TODO: implement (Person 1)
from app.models import AgentContext, AgentResult


def run(context: AgentContext) -> AgentResult:
    return AgentResult(
        agent_name="readme_agent",
        status="skipped",
        summary="Not yet implemented (Person 1).",
        output_files=[],
        issues=[],
        raw_output={},
    )
