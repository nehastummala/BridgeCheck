"""
BridgeCheck — FastAPI Backend
=============================
Endpoints:
  GET  /                          health check
  GET  /api/resources             list all resources
  POST /api/routing               check if Q3 should be skipped
  POST /api/adaptive-question     get the adaptive Q3 question for a barrier set
  POST /api/analyze               run full BridgeLogic engine, return results
  GET  /api/admin/stats           anonymous aggregate stats (no PII)
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func

from .database import engine, get_db, Base
from . import models, schemas
from .engine import (
    UserSession,
    run_bridgelogic,
    get_adaptive_question,
    should_skip_q3,
    compute_confidence,
)

# Create tables on startup (use Alembic migrations in production)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="BridgeCheck API",
    description="BridgeLogic™ Adaptive Barrier-Aware Decision Engine",
    version="1.0.0",
)

# CORS — update origins before going to production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",                    # local frontend dev server
        "http://localhost:5500",                    # VS Code Live Server
        "https://bridgecheck.org", 
        "https://bridge-check-olive.vercel.app",# production domain
        "https://bridge-check-xi.vercel.app",       # Vercel deployment
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── HEALTH ────────────────────────────────────────────────────
@app.get("/")
def health():
    return {"status": "ok", "engine": "BridgeLogic™ v1.0"}


# ── RESOURCES ─────────────────────────────────────────────────
@app.get("/api/resources", response_model=list[schemas.ResourceSchema])
def list_resources(db: Session = Depends(get_db)):
    """Return all active resources (for admin / debugging)."""
    resources = db.query(models.Resource).filter(models.Resource.is_active == True).all()
    return [
        schemas.ResourceSchema(
            id=r.id, name=r.name, description=r.description,
            cost_badge=r.cost_badge, tags=r.tags or [],
            access_modes=r.access_modes or [], links=r.links or [],
            why_text="", is_top_match=False, score=0, matched_barriers=[],
        )
        for r in resources
    ]


# ── ROUTING (should Q3 be skipped?) ───────────────────────────
@app.post("/api/routing", response_model=schemas.RoutingResponse)
def check_routing(req: schemas.AdaptiveQuestionRequest):
    """
    Called after Q2. Returns whether BridgeLogic has enough signal
    to skip the adaptive Q3 question.
    """
    session = UserSession(barriers=req.barriers)
    skip = should_skip_q3(session)
    conf = compute_confidence(session, partial=True)
    return schemas.RoutingResponse(
        skip_q3=skip,
        confidence=conf,
        message=(
            "High confidence detected — proceeding directly to access preferences."
            if skip else
            "BridgeLogic needs one more question to improve your recommendations."
        ),
    )


# ── ADAPTIVE QUESTION ─────────────────────────────────────────
@app.post("/api/adaptive-question", response_model=schemas.AdaptiveQuestionResponse)
def adaptive_question(req: schemas.AdaptiveQuestionRequest):
    """
    Returns the adaptive Q3 question tailored to the user's primary barrier.
    Also signals whether Q3 should be skipped entirely.
    """
    session = UserSession(barriers=req.barriers)
    qdata   = get_adaptive_question(session)
    skip    = should_skip_q3(session)
    return schemas.AdaptiveQuestionResponse(
        title    = qdata["title"],
        subtitle = qdata["subtitle"],
        options  = [schemas.AdaptiveQuestionOption(**o) for o in qdata["options"]],
        skip_q3  = skip,
    )


# ── ANALYZE (main BridgeLogic call) ───────────────────────────
@app.post("/api/analyze", response_model=schemas.AnalyzeResponse)
def analyze(req: schemas.AnalyzeRequest, db: Session = Depends(get_db)):
    """
    Full BridgeLogic™ engine run.
    Takes the user's complete session answers and returns:
      - Confidence score + reasons
      - BridgeLogic summary
      - Barrier profile with navigation-priority weights
      - Ranked resource matches with why-text
      - Action plan
    """
    session = UserSession(
        support_type    = req.support_type,
        barriers        = req.barriers,
        adaptive_answer = req.adaptive_answer,
        access_prefs    = req.access_prefs,
        zip_code        = req.zip_code,
        skipped_q3      = req.adaptive_answer is None,
    )

    result = run_bridgelogic(session, db)

      if not result["resources"]:
        fallback_resources = db.query(models.Resource).filter(models.Resource.is_active == True).limit(4).all()

        result["resources"] = [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "cost_badge": r.cost_badge,
                "tags": r.tags or [],
                "access_modes": r.access_modes or [],
                "links": r.links or [],
                "why_text": "This resource is included as a verified support option based on your preferences.",
                "is_top_match": i == 0,
                "score": 1,
                "matched_barriers": session.barriers,
            }
            for i, r in enumerate(fallback_resources)
        ]

    # Log anonymous aggregate data (no PII)
    _log_assessment(session, result, db)

    return schemas.AnalyzeResponse(
        confidence      = schemas.ConfidenceSchema(**result["confidence"]),
        summary         = schemas.SummarySchema(**result["summary"]),
        barrier_profile = [schemas.BarrierProfileItem(**b) for b in result["barrier_profile"]],
        why_reasons     = result["why_reasons"],
        resources       = [schemas.ResourceSchema(**r) for r in result["resources"]],
        action_plan     = [schemas.ActionStepSchema(**s) for s in result["action_plan"]],
        factors_analyzed= result["factors_analyzed"],
        zip_code        = result["zip_code"],
    )


# ── ADMIN STATS ───────────────────────────────────────────────
@app.get("/api/admin/stats")
def admin_stats(db: Session = Depends(get_db)):
    """
    Anonymous aggregate statistics only.
    No names, emails, IPs, or individual responses — just counts.
    """
    total = db.query(func.count(models.AssessmentLog.id)).scalar()
    if total == 0:
        return {"total_assessments": 0, "barrier_breakdown": {}, "top_support_types": []}

    # Barrier breakdown
    barrier_counts: dict[str, int] = {}
    logs = db.query(models.AssessmentLog).all()
    for log in logs:
        if log.primary_barrier:
            barrier_counts[log.primary_barrier] = barrier_counts.get(log.primary_barrier, 0) + 1

    # Support type breakdown
    type_counts: dict[str, int] = {}
    for log in logs:
        if log.support_type:
            type_counts[log.support_type] = type_counts.get(log.support_type, 0) + 1

    avg_confidence = sum(l.confidence for l in logs if l.confidence) / max(total, 1)

    return {
        "total_assessments":  total,
        "barrier_breakdown":  barrier_counts,
        "support_type_breakdown": type_counts,
        "avg_confidence":     round(avg_confidence, 1),
        "high_conf_skips":    sum(1 for l in logs if l.skipped_q3),
    }


# ── INTERNAL ──────────────────────────────────────────────────
def _log_assessment(session: UserSession, result: dict, db: Session):
    """Write one anonymous aggregate row per completed assessment."""
    try:
        top_id = result["resources"][0]["id"] if result["resources"] else None
        log = models.AssessmentLog(
            support_type    = session.support_type,
            barrier_count   = len(session.barriers),
            primary_barrier = session.barriers[0] if session.barriers else None,
            access_count    = len(session.access_prefs),
            has_zip         = bool(session.zip_code),
            skipped_q3      = session.skipped_q3,
            confidence      = result["confidence"]["score"],
            top_match_id    = top_id,
        )
        db.add(log)
        db.commit()
    except Exception:
        db.rollback()   # log failure should never break the user response
