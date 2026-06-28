"""
BridgeLogic™ — Adaptive Barrier-Aware Decision Engine
======================================================
Core algorithm for BridgeCheck. Handles:
  - Barrier profiling and priority weighting
  - Adaptive confidence scoring
  - Dynamic question routing (stop early if confidence is high)
  - Resource ranking via multi-factor scoring
  - Action plan generation
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from sqlalchemy.orm import Session
from . import models


# ─────────────────────────────────────────────────────────────
# BARRIER WEIGHTS
# Each barrier is assigned a navigation-priority weight (0–100)
# based on how strongly it predicts difficulty accessing care.
# Derived from SAMHSA access-to-care research literature.
# ─────────────────────────────────────────────────────────────
BARRIER_WEIGHTS: dict[str, int] = {
    "cost":      90,   # strongest predictor of unmet need
    "transport": 75,
    "privacy":   68,
    "waittime":  60,
    "language":  55,
    "info":      45,
}

BARRIER_LABELS: dict[str, str] = {
    "cost":      "Cost / no insurance",
    "transport": "No transportation",
    "privacy":   "Privacy or stigma",
    "waittime":  "Long wait times",
    "language":  "Language or cultural barriers",
    "info":      "Unsure where to start",
}

ACCESS_LABELS: dict[str, str] = {
    "inperson": "In-person",
    "video":    "Video / telehealth",
    "phone":    "Phone",
    "text":     "Text / chat",
}


# ─────────────────────────────────────────────────────────────
# ADAPTIVE Q3 QUESTION BANK
# Each primary barrier maps to a tailored follow-up question
# with its own options. This is what makes BridgeLogic adaptive.
# ─────────────────────────────────────────────────────────────
ADAPTIVE_QUESTIONS: dict[str, dict] = {
    "cost": {
        "title": "Would free or low-cost options make getting help possible?",
        "subtitle": "BridgeLogic detected cost as your primary barrier and will prioritize no-cost and sliding-scale resources.",
        "options": [
            {"value": "yes_free",    "label": "Yes — free options would make a real difference", "desc": "I can't afford sessions right now"},
            {"value": "yes_sliding", "label": "A sliding scale would work",                       "desc": "I can pay something, just not full price"},
            {"value": "insurance",   "label": "I have insurance but don't know what's covered",   "desc": "Help me find in-network options"},
        ],
    },
    "transport": {
        "title": "Would virtual appointments work better for you?",
        "subtitle": "BridgeLogic detected transportation as your primary barrier and will prioritize telehealth and remote options.",
        "options": [
            {"value": "yes_virtual", "label": "Yes — I need fully virtual options",          "desc": "Video, phone, or text from home"},
            {"value": "nearby",      "label": "I could do in-person if it's very close",     "desc": "Within walking distance or a short ride"},
            {"value": "mixed",       "label": "Either works depending on the day",            "desc": "I want flexibility"},
        ],
    },
    "privacy": {
        "title": "Would anonymous or low-profile support feel more comfortable?",
        "subtitle": "BridgeLogic detected privacy concerns and will prioritize anonymous, no-registration resources.",
        "options": [
            {"value": "anon",        "label": "Yes — I want to stay anonymous",              "desc": "No name, no records"},
            {"value": "confidential","label": "I'm okay with confidential (not anonymous)",  "desc": "Private provider with HIPAA protections"},
            {"value": "notsure",     "label": "I'm not sure yet",                            "desc": "Show me all options"},
        ],
    },
    "language": {
        "title": "What language or cultural background matters most?",
        "subtitle": "BridgeLogic will prioritize providers with multilingual staff and culturally informed approaches.",
        "options": [
            {"value": "spanish",    "label": "Spanish-speaking provider",      "desc": "Hablo español"},
            {"value": "cultural",   "label": "Culturally informed care",       "desc": "A provider who understands my background"},
            {"value": "other_lang", "label": "Another language or preference", "desc": "I'll specify when I contact the provider"},
        ],
    },
    "waittime": {
        "title": "How quickly do you need to connect with someone?",
        "subtitle": "BridgeLogic detected wait time as your primary barrier and will prioritize fast-access options.",
        "options": [
            {"value": "today",     "label": "Today or tomorrow",         "desc": "I need to talk to someone very soon"},
            {"value": "this_week", "label": "This week",                 "desc": "Within the next few days"},
            {"value": "flexible",  "label": "I'm flexible on timing",   "desc": "I can wait if the provider is a great fit"},
        ],
    },
    "info": {
        "title": "What feels like the best first step right now?",
        "subtitle": "BridgeLogic detected you're still figuring out where to start and will surface navigator-friendly resources.",
        "options": [
            {"value": "talk_someone",  "label": "Talk to someone who can guide me",     "desc": "A navigator or helpline I can call"},
            {"value": "self_guide",    "label": "See a list of options I can review",   "desc": "I'd rather research on my own first"},
            {"value": "crisis_first",  "label": "I think I need help urgently",         "desc": "Point me toward immediate support"},
        ],
    },
    "default": {
        "title": "How soon would you like to get started?",
        "subtitle": "This helps BridgeLogic prioritize immediate vs. longer-term resources.",
        "options": [
            {"value": "now",       "label": "As soon as possible",      "desc": "I need something right away"},
            {"value": "soon",      "label": "Within the next few weeks","desc": "I'm ready but taking my time"},
            {"value": "exploring", "label": "Just exploring for now",   "desc": "No rush"},
        ],
    },
}


# ─────────────────────────────────────────────────────────────
# USER SESSION — holds everything BridgeLogic knows so far
# ─────────────────────────────────────────────────────────────
@dataclass
class UserSession:
    support_type: Optional[str] = None          # q1
    barriers: list[str] = field(default_factory=list)   # q2 (multi)
    adaptive_answer: Optional[str] = None        # q3
    access_prefs: list[str] = field(default_factory=list)  # q4 (multi)
    zip_code: Optional[str] = None
    skipped_q3: bool = False


# ─────────────────────────────────────────────────────────────
# CONFIDENCE SCORING
# Returns 0–100. Calculated from completeness + consistency
# of the session data. Not a clinical score.
# ─────────────────────────────────────────────────────────────
def compute_confidence(session: UserSession, partial: bool = False) -> int:
    score = 50

    if session.support_type:
        score += 10

    n_barriers = len(session.barriers)
    if n_barriers >= 1:
        score += 10
    if n_barriers >= 3:
        score += 8   # more barriers = more signal

    if partial:
        return min(score, 78)

    if len(session.access_prefs) >= 1:
        score += 10
    if len(session.access_prefs) >= 2:
        score += 5
    if session.zip_code:
        score += 5
    if session.adaptive_answer and not session.skipped_q3:
        score += 4   # answered the adaptive question = better signal

    return min(score, 97)


# ─────────────────────────────────────────────────────────────
# CONFIDENCE ROUTING
# Decides whether to show Q3 or skip it.
# High confidence after Q2 → skip adaptive follow-up.
# ─────────────────────────────────────────────────────────────
CONFIDENCE_THRESHOLD = 75   # tune this as you gather real usage data

def should_skip_q3(session: UserSession) -> bool:
    """Return True if BridgeLogic has enough signal to skip Q3."""
    conf = compute_confidence(session, partial=True)
    return conf >= CONFIDENCE_THRESHOLD


# ─────────────────────────────────────────────────────────────
# ADAPTIVE QUESTION SELECTOR
# Picks the Q3 question branch based on the user's top barrier.
# ─────────────────────────────────────────────────────────────
def get_adaptive_question(session: UserSession) -> dict:
    primary = session.barriers[0] if session.barriers else "default"
    return ADAPTIVE_QUESTIONS.get(primary, ADAPTIVE_QUESTIONS["default"])


# ─────────────────────────────────────────────────────────────
# BARRIER PROFILE
# Returns each barrier with its weighted navigation priority,
# normalized relative to the user's highest-weight barrier.
# ─────────────────────────────────────────────────────────────
def build_barrier_profile(session: UserSession) -> list[dict]:
    barriers = session.barriers if session.barriers else ["info"]
    max_w = max(BARRIER_WEIGHTS.get(b, 45) for b in barriers)
    profile = []
    for b in barriers:
        w = BARRIER_WEIGHTS.get(b, 45)
        pct = round((w / max_w) * 100)
        profile.append({
            "key":      b,
            "label":    BARRIER_LABELS.get(b, b),
            "weight":   w,
            "priority": pct,   # normalized 0–100, relative to user's top barrier
        })
    # sort descending by weight
    profile.sort(key=lambda x: x["weight"], reverse=True)
    return profile


# ─────────────────────────────────────────────────────────────
# RESOURCE SCORING & RANKING
# Multi-factor scoring:
#   +4 per support type match
#   +3 per barrier match
#   +2 per access preference match
#   +1 urgency bonus (crisis/waittime signals)
# ─────────────────────────────────────────────────────────────
def score_resource(resource: models.Resource, session: UserSession) -> int:
    score = 0

    tags = resource.tags or []
    barriers = getattr(resource, "barriers", None) or tags
    access_modes = resource.access_modes or []

    if session.support_type and session.support_type in tags:
        score += 4

    for b in session.barriers:
        if b in barriers or b in tags:
            score += 3

    for a in session.access_prefs:
        if a in access_modes:
            score += 2

    if "crisis" in tags and (
        session.support_type == "crisis"
        or "waittime" in session.barriers
        or session.adaptive_answer in ("today", "this_week", "crisis_first")
    ):
        score += 1

    return score


def rank_resources(session: UserSession, db: Session, limit: int = 4) -> list[dict]:
    resources = db.query(models.Resource).all()

    scored = []

    for r in resources:
        tags = r.tags or []
        access_modes = r.access_modes or []

        sc = 0

        if session.support_type and session.support_type in tags:
            sc += 4

        matched_barriers = []
        for b in session.barriers:
            if b in tags:
                sc += 3
                matched_barriers.append(b)

        for a in session.access_prefs:
            if a in access_modes:
                sc += 2

        why_parts = []
        for b in matched_barriers[:2]:
            why_text = (r.why_text or {}).get(b)
            if why_text:
                why_parts.append(why_text)

        scored.append({
            "resource": r,
            "score": sc,
            "matched_barriers": matched_barriers,
            "why_text": " ".join(why_parts),
            "is_top_match": False,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)

    top = scored[:limit]
    if top:
        top[0]["is_top_match"] = True

    return top

# ─────────────────────────────────────────────────────────────
# WHY-PANEL REASONS
# Explains to the user, in plain English, why BridgeLogic
# chose the resources it did.
# ─────────────────────────────────────────────────────────────
def build_why_reasons(session: UserSession) -> list[str]:
    reasons = []
    if "cost" in session.barriers:
        reasons.append("remove financial barriers — all free or sliding-scale options shown")
    if "transport" in session.barriers or "video" in session.access_prefs or "phone" in session.access_prefs:
        reasons.append("offer telehealth or remote access")
    if "waittime" in session.barriers:
        reasons.append("have short or immediate wait times")
    if "privacy" in session.barriers:
        reasons.append("provide confidential or anonymous support")
    if "language" in session.barriers:
        reasons.append("offer multilingual or culturally informed services")
    if not reasons:
        reasons = [
            "match your stated support need",
            "are publicly available and verified",
        ]
    return reasons


# ─────────────────────────────────────────────────────────────
# NEXT STEP GENERATOR
# Produces the "Recommended next step" in the BridgeLogic summary.
# ─────────────────────────────────────────────────────────────
def recommended_next_step(session: UserSession, top_resource_name: str) -> str:
    if "cost" in session.barriers:
        return "Ask about sliding-scale or free options when you first call any provider."
    if "transport" in session.barriers:
        return "Start with a telehealth option — most matched resources offer same-week remote availability."
    if "privacy" in session.barriers:
        return "Start with an anonymous option like the NAMI helpline or 988 — no name required."
    if session.support_type == "crisis":
        return "Call or text 988 now — free, 24/7, confidential, no insurance needed."
    return f"Reach out to \"{top_resource_name}\" this week while this plan is fresh."


# ─────────────────────────────────────────────────────────────
# ACTION PLAN GENERATOR
# Returns an ordered list of concrete steps for the user.
# ─────────────────────────────────────────────────────────────
def build_action_plan(session: UserSession, top_resources: list[dict]) -> list[dict]:
    steps = []
    top_name = top_resources[0]["resource"].name if top_resources else "your top match"
    top_badge = top_resources[0]["resource"].cost_badge if top_resources else "low"

    if "cost" in session.barriers or "transport" in session.barriers:
        steps.append({
            "title": "Start with your top match today",
            "body": f'"{top_name}" is your best fit. '
                    + ("It's free — no insurance needed." if top_badge == "free"
                       else "Financial aid is available — ask when you first reach out."),
        })
    else:
        steps.append({
            "title": f"Reach out to \"{top_name}\"",
            "body": "This is your top BridgeLogic match. Contacting them this week gives you the best chance of a timely connection.",
        })

    if "cost" in session.barriers:
        steps.append({
            "title": "Ask about free or sliding-scale fees",
            "body": "Say \"I don't have insurance — do you offer sliding-scale or free options?\" when you call. Most resources listed here do.",
        })
    if "transport" in session.barriers or "video" in session.access_prefs:
        steps.append({
            "title": "Request a telehealth appointment",
            "body": "All starred resources offer remote options. You can often start within 48 hours without leaving home.",
        })
    if "language" in session.barriers:
        steps.append({
            "title": "Request language support upfront",
            "body": "All listed resources offer interpreter services or bilingual staff. Ask when you first contact them.",
        })
    if session.zip_code:
        steps.append({
            "title": f"Search locally near ZIP {session.zip_code}",
            "body": "Visit findtreatment.gov to find accredited providers in your area that accept your insurance or offer free care.",
        })
    steps.append({
        "title": "Save or share this plan",
        "body": "Print this page or copy the link. Consider sharing it with a trusted person in your life.",
    })
    return steps


# ─────────────────────────────────────────────────────────────
# MASTER ENGINE CALL
# Single entry point: takes a UserSession, returns everything
# the frontend needs to render the results page.
# ─────────────────────────────────────────────────────────────
def run_bridgelogic(session: UserSession, db: Session) -> dict:
    conf = compute_confidence(session)
    conf_label = "High" if conf >= 80 else "Medium" if conf >= 65 else "Moderate"

    primary = session.barriers[0] if session.barriers else "info"
    secondary = session.barriers[1] if len(session.barriers) > 1 else None
    access_pref = " / ".join(ACCESS_LABELS.get(a, a) for a in session.access_prefs) or "Not specified"

    ranked = rank_resources(session, db)
    top_name = ranked[0]["resource"].name if ranked else "your top match"

    return {
        "confidence": {
            "score": conf,
            "label": conf_label,
            "skipped_q3": session.skipped_q3,
            "reasons": _confidence_reasons(session, ranked, conf),
        },
        "summary": {
            "primary_barrier": BARRIER_LABELS.get(primary, "Not specified"),
            "secondary_barrier": BARRIER_LABELS.get(secondary, "None identified") if secondary else "None identified",
            "preferred_access": access_pref,
            "match_quality": conf_label,
            "next_step": recommended_next_step(session, top_name),
            "route": "High-confidence route" if session.skipped_q3 else "Standard route",
        },
        "barrier_profile": build_barrier_profile(session),
        "why_reasons": build_why_reasons(session),
        "resources": _serialize_resources(ranked),
        "action_plan": build_action_plan(session, ranked),
        "factors_analyzed": len(session.barriers) + 2,
        "zip_code": session.zip_code,
    }


def _confidence_reasons(session: UserSession, ranked: list, conf: int) -> list[dict]:
    reasons = []
    n = len(session.barriers)
    if n >= 1:
        reasons.append({"icon": "check", "text": f"{n} barrier{'s' if n>1 else ''} identified"})
    if len(ranked) >= 3:
        reasons.append({"icon": "check", "text": f"{len(ranked)} strong resource matches found"})
    if len(session.access_prefs) >= 2:
        reasons.append({"icon": "check", "text": "Access preferences well-specified"})
    if session.zip_code:
        reasons.append({"icon": "check", "text": f"Location context added (ZIP {session.zip_code})"})
    if session.skipped_q3:
        reasons.append({"icon": "check", "text": "High-confidence route — follow-up question not needed"})
    return reasons


def _serialize_resources(ranked: list[dict]) -> list[dict]:
    out = []
    for item in ranked:
        r = item["resource"]
        out.append({
            "id":               r.id,
            "name":             r.name,
            "description":      r.description,
            "cost_badge":       r.cost_badge,
            "tags":             r.tags or [],
            "access_modes":     r.access_modes or [],
            "links":            r.links or [],
            "why_text":         item["why_text"],
            "is_top_match":     item["is_top_match"],
            "score":            item["score"],
            "matched_barriers": item["matched_barriers"],
        })
    return out
