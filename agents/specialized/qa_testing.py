"""QA Testing Agent — tests running applications against specifications."""
from agents.core.base_agent import BaseAgent, AgentConfig, AgentType, EffortLevel
SYSTEM = """
<role>
You are the QA Testing Agent. Thoroughly test applications against sprint contracts.
Be SKEPTICAL — do not approve work that has genuine issues.
</role>
<testing_approach>
1. Read the sprint contract carefully
2. Test EVERY criterion — do not skip any
3. Test happy paths AND edge cases
4. Verify API endpoints return correct status codes
5. Check database state after operations
6. Test error handling with invalid inputs
7. Verify UI is accessible and responsive
</testing_approach>
<grading>
Rate each criterion: PASS / FAIL / PARTIAL
Provide specific remediation steps for any FAIL or PARTIAL.
Overall sprint passes ONLY if ALL critical criteria pass.
</grading>
"""
class QATestingAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentConfig(
            agent_type=AgentType.QA_TESTING,
            model="claude-opus-4-6",
            max_tokens=5000,
            effort=EffortLevel.MEDIUM,
            system_prompt=SYSTEM,
        ))
    def test_sprint(self, app_url: str, sprint_contract: str, task_id: str) -> str:
        task = f"""
<app_url>{app_url}</app_url>
<sprint_contract>{sprint_contract}</sprint_contract>
Test the application against every criterion in the sprint contract.
For each criterion provide:
- criterion: (exact text from contract)
- status: PASS / FAIL / PARTIAL
- evidence: (what you observed)
- remediation: (exact fix needed if FAIL/PARTIAL)
Return JSON with: overall_status, criteria_results (list), bugs_found (list),
recommendations (list), ready_for_release (bool).
"""
        return self.run(task=task, task_id=task_id)
