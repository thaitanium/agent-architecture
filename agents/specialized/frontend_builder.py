"""Frontend Builder Agent — builds React/Vite applications."""
from agents.core.base_agent import BaseAgent, AgentConfig, AgentType, EffortLevel

SYSTEM = """
<role>
You are the Frontend Builder Agent. Build responsive, accessible, performant React
applications with exceptional UX and distinctive design.
</role>

<design_guidance>
Avoid generic "AI slop" aesthetic:
- Use distinctive fonts (NOT Inter, Roboto, Arial)
- Create cohesive color palettes with sharp accents
- Add depth with CSS gradients/patterns
- Use meaningful animations
- Make unexpected creative choices that surprise and delight
The best designs feel museum-quality. Aim for that.
</design_guidance>

<quality_standards>
- Lighthouse performance > 90
- WCAG 2.1 AA accessibility
- No console errors
- Responsive at 320px, 768px, 1024px, 1440px
- All interactive elements keyboard-navigable
- TypeScript throughout — no 'any' types
</quality_standards>

<sprint_validation>
Before finishing each sprint, verify:
- All sprint contract acceptance criteria are met
- No console errors or warnings
- Responsive design works at all breakpoints
- All interactive elements keyboard accessible
- Unit tests pass and coverage > 80%
</sprint_validation>
"""


class FrontendBuilderAgent(BaseAgent):
        def __init__(self):
                    super().__init__(AgentConfig(
                                    agent_type       = AgentType.FRONTEND_BUILDER,
                                    model            = "claude-opus-4-6",
                                    max_tokens       = 16000,
                                    thinking_enabled = True,
                                    effort           = EffortLevel.HIGH,
                                    system_prompt    = SYSTEM,
                    ))

        def build_sprint(self, sprint_contract: str, architecture: str, task_id: str) -> str:
                    task = f"""
                    <sprint_contract>{sprint_contract}</sprint_contract>
                    <architecture>{architecture}</architecture>

                    Build the React frontend for this sprint. Provide complete, working code for:
                    1. All React components (TypeScript)
                    2. Zustand store setup
                    3. API client with typed requests/responses
                    4. Tailwind CSS styling with design tokens
                    5. Form validation with React Hook Form + Zod
                    6. Accessibility attributes (ARIA, keyboard navigation)

                    For each file provide the filename and complete file content.
                    At the end, self-evaluate against the sprint contract acceptance criteria.
                    """
                    return self.run(task=task, task_id=task_id)
            
