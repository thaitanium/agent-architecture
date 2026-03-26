"""
QA Testing Agent — tests running applications against sprint contracts.

Changes (v2):
- Accept optional playwright_tools list so the orchestrator can inject
  live-browser tools (playwright_navigate, playwright_click, etc.)
  - Add few-shot examples calibrating the evaluator toward skepticism
  - Keep system prompt skepticism language
  """
from typing import Optional, List, Dict, Any
from agents.core.base_agent import BaseAgent, AgentConfig, AgentType, EffortLevel

SYSTEM = """
<role>
You are the QA Testing Agent. Thoroughly test applications against sprint contracts.
Be SKEPTICAL — do not approve work that has genuine issues.
A "pass" means the feature works correctly end-to-end, not just that it renders.
</role>

<testing_approach>
1. Read the sprint contract carefully — understand each criterion before testing
2. Use playwright tools to NAVIGATE and INTERACT with the live application
3. Test EVERY criterion — do not skip any
4. Test happy paths AND edge cases AND error states
5. Verify API endpoints return correct HTTP status codes
6. Check database state after write operations
7. Test error handling: submit invalid inputs, empty forms, duplicate records
8. Verify UI is accessible (keyboard navigation, contrast) and responsive
</testing_approach>

<grading>
Rate each criterion: PASS / FAIL / PARTIAL

PASS   = criterion fully works as specified, verified by direct interaction
FAIL   = criterion does not work or is not implemented
PARTIAL = partially works but has meaningful gaps

Provide SPECIFIC remediation steps for any FAIL or PARTIAL — include file names
and line numbers when possible.

Overall sprint passes ONLY if ALL critical criteria pass.
</grading>

<few_shot_examples>
<example>
<criterion>User can create a new project with a name and description</criterion>
<testing_steps>
1. Navigate to /projects/new
2. Fill in name="Test Project" description="A test"
3. Click Submit
4. Verify redirect to project detail page
5. Verify project appears in /projects list
</testing_steps>
<good_evaluator_response>
{
  "criterion": "User can create a new project with name and description",
    "status": "PASS",
      "evidence": "Navigated to /projects/new, filled form, submitted. Redirected to /projects/1. Project appeared in list at /projects.",
        "remediation": null
        }
        </good_evaluator_response>
        <bad_evaluator_response>
        {
          "criterion": "User can create a new project",
            "status": "PASS",
              "evidence": "The form looks like it should work."
}
</bad_evaluator_response>
<note>Bad: did not actually test. Good: describes exact steps taken and observed outcomes.</note>
</example>

<example>
<criterion>Rectangle fill tool fills a rectangular area with selected tile on drag</criterion>
<testing_steps>
1. Navigate to level editor
2. Select a tile from the palette
3. Select the fill tool
4. Click and drag from (100,100) to (200,200)
5. Verify all tiles in that rectangle are filled
</testing_steps>
<good_evaluator_response>
{
  "criterion": "Rectangle fill tool fills rectangular area on drag",
    "status": "FAIL",
      "evidence": "Tool only places tiles at drag start and end points. The fillRectangle function in LevelEditor.tsx exists but mouseUp does not call it.",
        "remediation": "In LevelEditor.tsx, the onMouseUp handler should call fillRectangle(startPos, endPos) instead of just placeTile(endPos)."
}
</good_evaluator_response>
</example>
</few_shot_examples>
"""


class QATestingAgent(BaseAgent):
        def __init__(self, playwright_tools: Optional[List[Dict[str, Any]]] = None):
                    super().__init__(AgentConfig(
                                    agent_type    = AgentType.QA_TESTING,
                                    model         = "claude-opus-4-6",
                                    max_tokens    = 8000,
                                    effort        = EffortLevel.MEDIUM,
                                    thinking_enabled = True,
                                    thinking_budget  = 3000,
                                    system_prompt = SYSTEM,
                    ))
                    # Playwright MCP tools are injected by the orchestrator when a live
                    # app URL is available.  Without them the agent tests statically.
                    self._playwright_tools: Optional[Dict[str, Any]] = (
                        {t["name"]: self._noop_tool(t["name"]) for t in playwright_tools}
                        if playwright_tools else None
                    )

        @staticmethod
        def _noop_tool(name: str):
                    """Placeholder callable — replace with real Playwright MCP bindings."""
                    def _fn(**kwargs):
                                    return {"status": "ok", "tool": name, "kwargs": kwargs,
                                                                "note": "Replace this stub with real playwright-mcp bindings."}
                                return _fn

    def test_sprint(self, app_url: str, sprint_contract: str, task_id: str) -> str:
                task = f"""
                <app_url>{app_url}</app_url>
                <sprint_contract>{sprint_contract}</sprint_contract>

                Test the application against every criterion in the sprint contract.

                For EACH criterion:
                1. Use playwright tools to navigate and interact with the live app
                2. Record exactly what you did (steps taken)
                3. Record exactly what you observed
                4. Assign PASS / FAIL / PARTIAL

                Return JSON with:
                  overall_status      : "pass" | "fail" | "partial"
          criteria_results    : list of {{criterion, status, evidence, remediation}}
            bugs_found          : list of {{title, severity, description, steps_to_reproduce,
                                              expected_behavior, actual_behavior}}
                                                recommendations     : list of strings
                                                  ready_for_release   : bool
                                                  """
                return self.run(
                    task    = task,
                    task_id = task_id,
                    tools   = self._playwright_tools,
                )
        
