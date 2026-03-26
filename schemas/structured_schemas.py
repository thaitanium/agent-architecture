"""
Pydantic models for all agent outputs.
Used with Claude structured outputs for type-safe, validated responses.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
class FeaturePriority(str, Enum):
    MUST   = "must"
    SHOULD = "should"
    COULD  = "could"
    WONT   = "wont"
class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"
class TestStatus(str, Enum):
    PASS    = "pass"
    FAIL    = "fail"
    SKIP    = "skip"
    PARTIAL = "partial"
# ── Product Manager ──────────────────────────────────────────────────
class Feature(BaseModel):
    name:                str
    priority:            FeaturePriority
    description:         str
    acceptance_criteria: List[str]
    estimated_effort:    Optional[str] = None
    dependencies:        List[str]     = Field(default_factory=list)
class SuccessMetric(BaseModel):
    metric:      str
    target:      str
    measurement: str
    timeline:    str
class RoadmapPhase(BaseModel):
    phase_number:     int
    name:             str
    features:         List[str]
    duration_weeks:   int
    success_criteria: List[str]
class ProductSpecification(BaseModel):
    product_name:          str
    overview:              str
    must_have_features:    List[Feature]
    should_have_features:  List[Feature]    = Field(default_factory=list)
    success_metrics:       List[SuccessMetric]
    technical_constraints: List[str]        = Field(default_factory=list)
    roadmap:               List[RoadmapPhase]
# ── Technical Architect ──────────────────────────────────────────────
class APIEndpoint(BaseModel):
    path:                   str
    method:                 str
    description:            str
    request_body:           Optional[Dict[str, Any]] = None
    response_schema:        Dict[str, Any]
    authentication_required: bool = False
    error_codes:            Dict[int, str]  = Field(default_factory=dict)
class DatabaseTable(BaseModel):
    name:        str
    description: str
    columns:     Dict[str, Dict[str, Any]]
    primary_key: str
    foreign_keys: List[Dict[str, str]] = Field(default_factory=list)
    indexes:      List[Dict[str, Any]] = Field(default_factory=list)
class TechnicalArchitecture(BaseModel):
    technology_stack:      Dict[str, Any]
    system_components:     List[Dict[str, Any]]
    api_endpoints:         List[APIEndpoint]
    database_tables:       List[DatabaseTable]
    security_architecture: Dict[str, Any]
    deployment_strategy:   Dict[str, Any]
    risks:                 List[Dict[str, str]] = Field(default_factory=list)
# ── QA Testing ───────────────────────────────────────────────────────
class BugReport(BaseModel):
    title:               str
    severity:            Severity
    description:         str
    steps_to_reproduce:  List[str]
    expected_behavior:   str
    actual_behavior:     str
    remediation_notes:   Optional[str] = None
class CriterionResult(BaseModel):
    criterion:   str
    status:      TestStatus
    evidence:    str
    remediation: Optional[str] = None
class QAReport(BaseModel):
    overall_status:    str
    criteria_results:  List[CriterionResult]
    bugs_found:        List[BugReport]   = Field(default_factory=list)
    recommendations:   List[str]         = Field(default_factory=list)
    ready_for_release: bool
# ── Code Quality ─────────────────────────────────────────────────────
class CodeIssue(BaseModel):
    file:        str
    line:        Optional[int] = None
    severity:    Severity
    type:        str
    description: str
    fix:         str
class CodeQualityReport(BaseModel):
    overall_score:             int
    issues:                    List[CodeIssue]
    refactoring_opportunities: List[Dict[str, str]] = Field(default_factory=list)
    summary:                   str
# ── Orchestration ─────────────────────────────────────────────────────
class AgentTask(BaseModel):
    task_id:     str
    agent_type:  str
    description: str
    status:      str
    input_data:  Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    created_at:  datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
class WorkflowExecution(BaseModel):
    workflow_id:        str
    project_name:       str
    user_requirement:   str
    status:             str
    tasks:              List[AgentTask]
    total_cost:         float = 0.0
    total_tokens_used:  int   = 0
    started_at:         datetime = Field(default_factory=datetime.now)
    completed_at:       Optional[datetime] = None
    final_deliverables: Dict[str, str] = Field(default_factory=dict)
