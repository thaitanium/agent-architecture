"""Code Quality Agent — reviews code for quality, security, and best practices.

Routes to claude-sonnet-4-6 (not Opus) for cost efficiency — code review
does not require the deep reasoning needed for full-stack generation.
"""
from agents.core.base_agent import BaseAgent, AgentConfig, AgentType, EffortLevel

SYSTEM = """
<role>
You are the Code Quality Agent. Review code for quality, security vulnerabilities,
performance issues, and maintainability. Be constructive but thorough.
</role>

<review_checklist>
Security:
- No SQL injection (parameterised queries / ORM)
- No hardcoded secrets
- Input validation on all user data
- Proper authentication checks

Performance:
- No N+1 queries
- Appropriate indexes used
- No unnecessary re-renders (frontend)
- Efficient algorithms

Maintainability:
- Single Responsibility Principle
- Clear variable/function names
- No duplicated code (DRY)
- Adequate comments for complex logic

Testing:
- Critical paths have unit tests
- Error cases are tested
</review_checklist>
"""


class CodeQualityAgent(BaseAgent):
        def __init__(self):
                    super().__init__(AgentConfig(
                                    agent_type=AgentType.CODE_QUALITY,
                                    model="claude-sonnet-4-6",   # Sonnet for cost efficiency
                                    max_tokens=8192,
                                    thinking_enabled=False,       # Code review does not need deep reasoning
                                    effort=EffortLevel.MEDIUM,
                                    system_prompt=SYSTEM,
                    ))

        def review_code(self, code_files: str, task_id: str) -> str:
                    task = f"""
                    <code_files>{code_files}</code_files>

                    Review these code files. For each issue found provide:
                    - file: (filename)
                    - line: (line number if applicable)
                    - severity: critical / high / medium / low
                    - type: security / performance / maintainability / testing
                    - description: (what the issue is)
                    - fix: (exact recommended fix)

                    Return JSON with: overall_score (0-100), issues (list),
                    refactoring_opportunities (list), summary (string).
                    """
                    return self.run(task=task, task_id=task_id)
