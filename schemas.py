"""
Pydantic schemas — request/response shapes for the API.
Keeps models separate from API contracts.
"""

from pydantic import BaseModel, Field
from typing import Optional


# ── REQUESTS ─────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    support_type:    str              = Field(..., description="q1 answer: therapy|crisis|peer|substance|medication")
    barriers:        list[str]        = Field(..., description="q2 answers (multi-select)")
    adaptive_answer: Optional[str]    = Field(None, description="q3 adaptive follow-up answer (may be null if skipped)")
    access_prefs:    list[str]        = Field(..., description="q4 answers (multi-select)")
    zip_code:        Optional[str]    = Field(None, min_length=5, max_length=5, description="US ZIP code (optional)")

    class Config:
        json_schema_extra = {
            "example": {
                "support_type": "therapy",
                "barriers": ["cost", "transport"],
                "adaptive_answer": "yes_virtual",
                "access_prefs": ["video", "phone"],
                "zip_code": "10001",
            }
        }


class AdaptiveQuestionRequest(BaseModel):
    barriers: list[str] = Field(..., description="Barriers selected in q2")

    class Config:
        json_schema_extra = {"example": {"barriers": ["cost", "transport"]}}


# ── RESPONSES ─────────────────────────────────────────────────

class ConfidenceSchema(BaseModel):
    score:      int
    label:      str
    skipped_q3: bool
    reasons:    list[dict]


class SummarySchema(BaseModel):
    primary_barrier:   str
    secondary_barrier: str
    preferred_access:  str
    match_quality:     str
    next_step:         str
    route:             str


class BarrierProfileItem(BaseModel):
    key:      str
    label:    str
    weight:   int
    priority: int


class ResourceSchema(BaseModel):
    id:               int
    name:             str
    description:      str
    cost_badge:       str
    tags:             list[str]
    access_modes:     list[str]
    links:            list[dict]
    why_text:         str
    is_top_match:     bool
    score:            int
    matched_barriers: list[str]


class ActionStepSchema(BaseModel):
    title: str
    body:  str


class AnalyzeResponse(BaseModel):
    confidence:       ConfidenceSchema
    summary:          SummarySchema
    barrier_profile:  list[BarrierProfileItem]
    why_reasons:      list[str]
    resources:        list[ResourceSchema]
    action_plan:      list[ActionStepSchema]
    factors_analyzed: int
    zip_code:         Optional[str]


class AdaptiveQuestionOption(BaseModel):
    value: str
    label: str
    desc:  str


class AdaptiveQuestionResponse(BaseModel):
    title:    str
    subtitle: str
    options:  list[AdaptiveQuestionOption]
    skip_q3:  bool   # True if confidence is high enough to skip this question


class RoutingResponse(BaseModel):
    skip_q3:    bool
    confidence: int
    message:    str
