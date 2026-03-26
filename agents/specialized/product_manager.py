"""Product Manager Agent — expands requirements into full product specs."""
from agents.core.base_agent import BaseAgent, AgentConfig, AgentType, EffortLevel
SYSTEM = """
<role>
You are the Product Manager Agent. Transform user requirements into comprehensive,
developer-ready product specifications using MoSCoW prioritisation.
</role>
<output_format>
Return valid JSON with keys:
product_name, overview, must_have_features, should_have_features,
success_metrics, technical_constraints, roadmap
Each feature must include: name, description, acceptance_criteria (list).
</output_format>
"""
class ProductManagerAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentConfig(
            agent_type=AgentType.PRODUCT_MANAGER,
            model="claude-opus-4-6",
            max_tokens=4096,
            effort=EffortLevel.HIGH,
            system_prompt=SYSTEM,
        ))
    def create_spec(self, user_requirement: str, task_id: str) -> str:
        task = f"""
<user_input>{user_requirement}</user_input>
Expand this into a full product specification. Include:
1. Product overview (2-3 sentences)
2. 5-10 Must-Have features with acceptance criteria
3. 3-5 Should-Have features
4. 3 measurable success metrics
5. Technical constraints
6. 4-phase roadmap
Return valid JSON.
"""
        return self.run(task=task, task_id=task_id)
