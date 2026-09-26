# Interface stub added by Person 4 — do not implement logic here.
# TODO: implement (Person 2)
from app.models import AgentContext, AgentResult


def run(context: AgentContext) -> AgentResult:
    return AgentResult(
        agent_name="example_validator",
        status="skipped",
        summary="Not yet implemented (Person 2).",
        output_files=[],
        issues=[],
        raw_output={},
    )
