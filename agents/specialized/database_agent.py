"""Database Agent — designs PostgreSQL schemas and migrations."""
from agents.core.base_agent import BaseAgent, AgentConfig, AgentType, EffortLevel

SYSTEM = """
<role>
You are the Database Agent. Design correct, performant, maintainable PostgreSQL
schemas. Data integrity is paramount.
</role>

<standards>
- Normalised to 3NF minimum
- Foreign key constraints with CASCADE where appropriate
- NOT NULL constraints enforced
- Indexes on all foreign keys and frequently queried columns
- All migrations reversible (up/down via Alembic)
- Parameterised queries only (via ORM — never raw SQL)
- Use created_at/updated_at timestamps on all tables
</standards>
"""


class DatabaseAgent(BaseAgent):
        def __init__(self):
                    super().__init__(AgentConfig(
                                    agent_type       = AgentType.DATABASE_AGENT,
                                    model            = "claude-opus-4-6",
                                    max_tokens       = 8192,
                                    thinking_enabled = True,
                                    effort           = EffortLevel.MEDIUM,
                                    system_prompt    = SYSTEM,
                    ))

        def design_schema(self, product_spec: str, architecture: str, task_id: str) -> str:
                    task = f"""
                    <product_spec>{product_spec}</product_spec>
                    <architecture>{architecture}</architecture>

                    Design the complete PostgreSQL database schema. Provide:
                    1. CREATE TABLE statements for all tables with constraints
                    2. All indexes (foreign keys + frequently queried columns)
                    3. Alembic migration files (up and down)
                    4. Docker Compose database service config
                    5. SQLAlchemy model classes
                    6. ER diagram (ASCII art)

                    Return as a structured JSON object with sections:
                    tables, indexes, migrations, docker_config, models.
                    """
                    return self.run(task=task, task_id=task_id)
            
