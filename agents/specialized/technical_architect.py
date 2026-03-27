"""Technical Architect Agent — designs system architecture from product spec."""
from agents.core.base_agent import BaseAgent, AgentConfig, AgentType, EffortLevel

SYSTEM = """
<role>
You are the Technical Architect Agent. Design complete, production-ready technical
architectures. Balance innovation, maintainability, scalability, and team capability.
</role>

<stack_defaults>
Frontend:  React 18 + Vite + Tailwind CSS + Zustand
Backend:   FastAPI + Python 3.11 + SQLAlchemy
Database:  PostgreSQL (prod) / SQLite (dev)
Auth:      JWT
Deploy:    Docker + GitHub Actions
</stack_defaults>

<output_format>
When returning structured output, call the structured_output tool with a JSON object
containing: technology_stack, system_components, api_endpoints, database_schema,
security_architecture, deployment_strategy, risks.
</output_format>

<decision_framework>
For each architectural decision, document:
1. Problem it solves (what would fail without it?)
2. Trade-offs (what do we gain/lose?)
3. Scalability implications (how does it handle 10x growth?)
</decision_framework>
"""


class TechnicalArchitectAgent(BaseAgent):
        def __init__(self):
                    super().__init__(AgentConfig(
                                    agent_type       = AgentType.TECHNICAL_ARCHITECT,
                                    model            = "claude-opus-4-6",
                                    max_tokens       = 8192,
                                    thinking_enabled = True,
                                    effort           = EffortLevel.HIGH,
                                    system_prompt    = SYSTEM,
                    ))

        def design_architecture(self, product_spec: str, task_id: str) -> str:
                    task = f"""
                    <product_spec>{product_spec}</product_spec>

                    Design the complete technical architecture. Provide:
                    1. Full technology stack with justification for each choice
                    2. System components and data flow (ASCII diagram)
                    3. All API endpoints (path, method, request/response schemas)
                    4. Complete database schema (tables, columns, indexes, foreign keys)
                    5. Authentication and security design
                    6. Deployment strategy (environments, CI/CD, rollback plan)
                    7. Key risks and mitigations

                    Call the structured_output tool to return your response as valid JSON.
                    """
                    return self.run(task=task, task_id=task_id)
            
