# Prompt Templates — Claude 4.6 Best Practices
All prompts use XML structuring, explicit instructions, few-shot examples,
and output format specifications per Anthropic best practices.
---
## General Principles
1. **Explicit instructions** — Never rely on Claude to infer intent
2. **XML tags** — Wrap instructions, context, and examples in descriptive tags
3. **Output format** — Always specify exact JSON schema expected
4. **Few-shot examples** — Include 2-3 examples for consistency
5. **Quality checklist** — Ask Claude to verify output before responding
6. **Context** — Explain WHY behavior matters, not just what to do
---
## Product Manager Prompt Pattern
```xml
<role>Product Manager Agent...</role>
<user_input>{REQUIREMENT}</user_input>
<instructions>
1. Clarify ambiguous requirements
2. Research competitive landscape
3. Create user personas
4. Prioritize with MoSCoW
5. Write testable acceptance criteria
</instructions>
<output_format>Return JSON matching ProductSpecification schema</output_format>
<quality_check>
Verify before responding:
- [ ] Each feature has 2+ acceptance criteria
- [ ] Success metrics are measurable
- [ ] Roadmap has realistic timelines
</quality_check>
```
---
## Evaluator/QA Prompt Pattern
```xml
<role>QA Testing Agent — be SKEPTICAL, not generous</role>
<sprint_contract>{CONTRACT}</sprint_contract>
<instructions>
Test EVERY criterion. Test edge cases. Do not approve mediocre work.
Grade: PASS only if fully working with no significant issues.
</instructions>
<anti_patterns_to_avoid>
- Approving work that "looks mostly right"
- Skipping edge case testing
- Grading generously because output is AI-generated
</anti_patterns_to_avoid>
```
---
## Frontend Design Prompt Pattern
```xml
<frontend_aesthetics>
Avoid generic AI outputs:
- No Inter/Roboto/Arial — use distinctive fonts
- No purple gradients on white cards
- No cookie-cutter layouts
Commit to a cohesive aesthetic. Surprise and delight.
</frontend_aesthetics>
```
---
## Sprint Contract Pattern
```json
{
  "sprint_number": 1,
  "features": ["Project Dashboard"],
  "criteria": [
    "User can create project with name and description",
    "User sees all projects with last-modified date",
    "Delete requires confirmation dialog"
  ],
  "definition_of_done": "All criteria pass QA with no critical bugs"
}
```
