"""Product Manager Agent — expands requirements into full product specs."""
from agents.core.base_agent import BaseAgent, AgentConfig, AgentType, EffortLevel

SYSTEM = """
<role>
You are the Product Manager Agent. Transform user requirements into comprehensive,
developer-ready product specifications using MoSCoW prioritisation.
</role>

<output_format>
When returning structured output, call the structured_output tool with a JSON object
containing these keys:
  product_name, overview, must_have_features, should_have_features,
    success_metrics, technical_constraints, roadmap

    Each feature must include: name, description, acceptance_criteria (list).
    </output_format>

    <few_shot_example>
    <input>Create a 2D retro game maker</input>
    <spec_excerpt>
    {
      "product_name": "RetroForge",
        "overview": "A web-based creative studio for designing 2D retro-style games...",
          "must_have_features": [
              {
                    "name": "Project Dashboard",
                          "description": "Central hub for creating and managing game projects",
                                "acceptance_criteria": [
                                        "User can create a new project with name and description",
                                                "User sees all projects with last-modified date",
                                                        "User can delete projects with a confirmation dialog"
      ]
          }
            ],
              "success_metrics": [
                  "1000+ active monthly users by month 6",
                      "Average session duration > 30 minutes"
  ]
  }
  </spec_excerpt>
  </few_shot_example>
  """

FEW_SHOT_PROMPT = """
Before creating the spec, review this example of a good product specification:

<example_spec>
Product: RetroForge (2D retro game maker)
- Product overview (2-3 sentences explaining what it is and who it is for)
- Must-Have features with 2-4 testable acceptance criteria each
- Should-Have features (important but not MVP-blocking)
- 3 SMART success metrics (Specific, Measurable, Achievable, Relevant, Time-bound)
- Technical constraints (platform, compliance, integrations)
- 4-phase roadmap with feature assignments and duration estimates
</example_spec>
"""


class ProductManagerAgent(BaseAgent):
        def __init__(self):
                    super().__init__(AgentConfig(
                                    agent_type       = AgentType.PRODUCT_MANAGER,
                                    model            = "claude-opus-4-6",
                                    max_tokens       = 8192,
                                    thinking_enabled = True,
                                    effort           = EffortLevel.HIGH,
                                    system_prompt    = SYSTEM,
                    ))

        def create_spec(self, user_requirement: str, task_id: str) -> str:
                    task = f"""
                    {FEW_SHOT_PROMPT}

                    <user_input>{user_requirement}</user_input>

                    Expand this into a full product specification. Include:
                    1. Product overview (2-3 sentences)
                    2. 5-10 Must-Have features with 2-4 testable acceptance criteria each
                    3. 3-5 Should-Have features
                    4. 3 SMART success metrics
                    5. Technical constraints
                    6. 4-phase roadmap

                    Call the structured_output tool to return your response as valid JSON.
                    """
                    return self.run(task=task, task_id=task_id)
            
