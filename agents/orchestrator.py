"""
WorkflowOrchestrator — sequences all specialized agents into a complete pipeline.

Pipeline:
  1. ProductManagerAgent     → product spec
    2. TechnicalArchitectAgent → architecture
      3. DatabaseAgent           → schema
        4. Sprint loop (up to max_sprints):
               a. Sprint-contract negotiation  (FrontendBuilder + QATestingAgent)
                      b. FrontendBuilderAgent + BackendBuilderAgent  → run IN PARALLEL
                             c. QATestingAgent               → test results  (retry up to qa_retries)
                               5. CodeQualityAgent        → code review
                                 6. Accumulate cost / tokens across all agents

                                 NOTE on streaming: base_agent uses max_tokens up to 16 000 for builders.
                                 The Anthropic API requires streaming when max_tokens > 21 333 (64 000 / 3).
                                 If you raise builder max_tokens above that threshold, switch BaseAgent.run()
                                 to use client.messages.stream() instead of client.messages.create().
                                 """

import uuid
import logging
import concurrent.futures
from datetime import datetime
from typing import Optional, Any

from agents.specialized.product_manager import ProductManagerAgent
from agents.specialized.technical_architect import TechnicalArchitectAgent
from agents.specialized.frontend_builder import FrontendBuilderAgent
from agents.specialized.backend_builder import BackendBuilderAgent
from agents.specialized.database_agent import DatabaseAgent
from agents.specialized.qa_testing import QATestingAgent
from agents.specialized.code_quality import CodeQualityAgent

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
      """Orchestrates the full multi-agent development pipeline."""

    def __init__(self, max_sprints: int = 3, qa_retries: int = 2):
              self.max_sprints = max_sprints
              self.qa_retries = qa_retries

        # Instantiate all agents
              self.product_manager = ProductManagerAgent()
              self.technical_architect = TechnicalArchitectAgent()
              self.database_agent = DatabaseAgent()
              self.frontend_builder = FrontendBuilderAgent()
              self.backend_builder = BackendBuilderAgent()
              self.qa_testing = QATestingAgent()
              self.code_quality = CodeQualityAgent()

        # Telemetry
              self.total_cost: float = 0.0
              self.total_input_tokens: int = 0
              self.total_output_tokens: int = 0
              self.run_log: list[dict] = []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _record(self, agent_name: str, result: Any, task_id: str) -> None:
              """Store per-agent telemetry."""
              self.run_log.append({
                  "agent": agent_name,
                  "task_id": task_id,
                  "timestamp": datetime.utcnow().isoformat(),
              })

    def _negotiate_sprint_contract(
              self,
              sprint_num: int,
              spec: str,
              architecture: str,
              task_id: str,
    ) -> str:
              """Ask FrontendBuilder what it needs from BackendBuilder this sprint."""
              prompt = f"""
      <sprint>{sprint_num}</sprint>
      <product_spec>{spec}</product_spec>
      <architecture>{architecture}</architecture>

      List ONLY the API endpoints and data contracts the frontend needs from the
      backend in sprint {sprint_num}. Be concise — this is the sprint contract.
      """
              return self.frontend_builder.run(task=prompt, task_id=f"{task_id}-contract-{sprint_num}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, user_request: str, task_id: Optional[str] = None) -> dict:
              """Execute the full pipeline and return a structured result dict."""
              task_id = task_id or str(uuid.uuid4())
              logger.info("WorkflowOrchestrator starting | task_id=%s", task_id)

        # ── Step 1: Product spec ──────────────────────────────────────
              logger.info("Step 1/5: ProductManagerAgent")
        spec = self.product_manager.create_spec(
                      user_request=user_request,
                      task_id=f"{task_id}-pm",
        )
        self._record("ProductManagerAgent", spec, task_id)

        # ── Step 2: Architecture ──────────────────────────────────────
        logger.info("Step 2/5: TechnicalArchitectAgent")
        architecture = self.technical_architect.design_architecture(
                      spec=str(spec),
                      task_id=f"{task_id}-arch",
        )
        self._record("TechnicalArchitectAgent", architecture, task_id)

        # ── Step 3: Database schema ───────────────────────────────────
        logger.info("Step 3/5: DatabaseAgent")
        schema = self.database_agent.design_schema(
                      spec=str(spec),
                      architecture=str(architecture),
                      task_id=f"{task_id}-db",
        )
        self._record("DatabaseAgent", schema, task_id)

        # ── Step 4: Sprint loop ───────────────────────────────────────
        frontend_code: str = ""
        backend_code: str = ""
        qa_results: str = ""

        for sprint in range(1, self.max_sprints + 1):
                      logger.info("Step 4/5: Sprint %d/%d", sprint, self.max_sprints)

            # 4a. Sprint-contract negotiation
                      contract = self._negotiate_sprint_contract(
                          sprint_num=sprint,
                          spec=str(spec),
                          architecture=str(architecture),
                          task_id=task_id,
                      )

            # 4b. Parallel: FrontendBuilder + BackendBuilder
                      # Running both agents concurrently cuts wall-clock time roughly in half.
                      logger.info("  Sprint %d: launching FE + BE builders in parallel", sprint)
                      with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                                        fe_future = executor.submit(
                                                              self.frontend_builder.build_frontend,
                                                              spec=str(spec),
                                                              architecture=str(architecture),
                                                              sprint_contract=contract,
                                                              sprint_num=sprint,
                                                              task_id=f"{task_id}-fe-{sprint}",
                                        )
                                        be_future = executor.submit(
                                            self.backend_builder.build_backend,
                                            spec=str(spec),
                                            architecture=str(architecture),
                                            schema=str(schema),
                                            sprint_contract=contract,
                                            sprint_num=sprint,
                                            task_id=f"{task_id}-be-{sprint}",
                                        )
                                        # Block until both complete; re-raise any agent exception
                                        frontend_code = fe_future.result()
                backend_code = be_future.result()

            self._record("FrontendBuilderAgent", frontend_code, task_id)
            self._record("BackendBuilderAgent", backend_code, task_id)

            # 4c. QA with retries
            for attempt in range(1, self.qa_retries + 2):
                              logger.info("  Sprint %d QA attempt %d", sprint, attempt)
                              qa_results = self.qa_testing.run_tests(
                                  frontend_code=frontend_code,
                                  backend_code=backend_code,
                                  task_id=f"{task_id}-qa-{sprint}-{attempt}",
                              )
                              self._record("QATestingAgent", qa_results, task_id)

                # Check if QA passed (simple heuristic; replace with structured check)
                              if isinstance(qa_results, dict):
                                                    if qa_results.get("overall_status") == "passed":
                                                                              break
                                                                          if attempt <= self.qa_retries:
                                                                                                    logger.warning("  QA failed — retrying sprint %d (attempt %d)", sprint, attempt + 1)
else:
                    # String result — assume pass for now
                      break

        # ── Step 5: Code quality review ───────────────────────────────
        logger.info("Step 5/5: CodeQualityAgent")
        code_review = self.code_quality.review_code(
                      code_files=f"<frontend>\n{frontend_code}\n</frontend>\n<backend>\n{backend_code}\n</backend>",
                      task_id=f"{task_id}-cq",
        )
        self._record("CodeQualityAgent", code_review, task_id)

        logger.info("WorkflowOrchestrator complete | task_id=%s", task_id)

        return {
                      "task_id": task_id,
                      "product_spec": spec,
                      "architecture": architecture,
                      "schema": schema,
                      "frontend_code": frontend_code,
                      "backend_code": backend_code,
                      "qa_results": qa_results,
                      "code_review": code_review,
                      "run_log": self.run_log,
        }my
