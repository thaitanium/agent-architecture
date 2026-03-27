"""Backend Builder Agent — builds FastAPI applications."""
from agents.core.base_agent import BaseAgent, AgentConfig, AgentType, EffortLevel

SYSTEM = """
<role>
You are the Backend API Builder Agent. Build robust, scalable, secure FastAPI
applications. Correctness and security are non-negotiable.
</role>

<quality_standards>
- All endpoints validated with Pydantic
- JWT authentication enforced on protected routes
- No raw SQL — use SQLAlchemy ORM only
- Comprehensive error handling with meaningful messages
- Structured JSON logging with request IDs
- API response times < 500ms for non-heavy operations
- No N+1 query problems
- Parameterised queries via ORM (no SQL injection)
</quality_standards>

<sprint_validation>
Before finishing each sprint, verify:
- All endpoints from the contract are implemented
- All endpoints return correct HTTP status codes
- Request validation works (test with invalid data)
- Authentication/authorization enforced
- Error handling comprehensive
- All tests passing
</sprint_validation>
"""


class BackendBuilderAgent(BaseAgent):
        def __init__(self):
                    super().__init__(AgentConfig(
                                    agent_type       = AgentType.BACKEND_BUILDER,
                                    model            = "claude-opus-4-6",
                                    max_tokens       = 16000,
                                    thinking_enabled = True,
                                    effort           = EffortLevel.HIGH,
                                    system_prompt    = SYSTEM,
                    ))

        def build_sprint(self, sprint_contract: str, db_schema: str, task_id: str) -> str:
                    task = f"""
                    <sprint_contract>{sprint_contract}</sprint_contract>
                    <database_schema>{db_schema}</database_schema>

                    Build the FastAPI backend for this sprint. Provide complete, working code for:
                    1. FastAPI router files with all endpoints
                    2. SQLAlchemy models
                    3. Pydantic request/response schemas
                    4. Authentication middleware
                    5. Error handling
                    6. Database session management

                    For each file provide the filename and complete file content.
                    At the end, self-evaluate against the sprint contract acceptance criteria.
                    """
                    return self.run(task=task, task_id=task_id)
            
