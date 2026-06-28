"""
seed.py — populate the resource database with verified mental health resources.
Run once: python seed.py

All resources verified against:
  - SAMHSA (findtreatment.gov)
  - HRSA (findahealthcenter.hrsa.gov)
  - NAMI (nami.org)
  - Official organization websites

Last verified: June 2026
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal, engine, Base
from app import models

Base.metadata.create_all(bind=engine)

RESOURCES = [
    {
        "name":        "988 Suicide & Crisis Lifeline",
        "description": "Free, confidential crisis support available 24/7 by call or text. "
                       "Spanish-language line available. No insurance or ID required.",
        "cost_badge":  "free",
        "tags":        ["crisis", "peer"],
        "barriers":    ["cost", "privacy", "info"],
        "access_modes":["phone", "text"],
        "links": [
            {"label": "Call 988",    "url": "tel:988",              "icon": "ti-phone",         "primary": True},
            {"label": "Text 988",    "url": "sms:988",              "icon": "ti-message",       "primary": False},
            {"label": "Visit site",  "url": "https://988lifeline.org", "icon": "ti-external-link","primary": False},
        ],
        "why_text": {
            "cost":    "Completely free — no insurance, no ID, no registration required.",
            "privacy": "Anonymous — counselors do not ask for your name.",
            "info":    "Can walk you through next steps and local resources while on the call.",
        },
    },
    {
        "name":        "Community Mental Health Centers (FQHCs)",
        "description": "Federally-funded clinics offering therapy, psychiatry, and case management "
                       "on a sliding-scale fee. Over 1,400 locations nationwide.",
        "cost_badge":  "free",
        "tags":        ["therapy", "peer", "medication", "substance"],
        "barriers":    ["cost", "transport", "language"],
        "access_modes":["inperson", "phone"],
        "links": [
            {"label": "Find a clinic", "url": "https://findahealthcenter.hrsa.gov", "icon": "ti-map-pin", "primary": True},
            {"label": "Call HRSA",     "url": "tel:18006218335",                   "icon": "ti-phone",   "primary": False},
        ],
        "why_text": {
            "cost":      "FQHCs cannot turn away patients due to inability to pay — fees can be set to $0 for lowest-income clients.",
            "language":  "Most FQHCs offer interpreter services and bilingual staff.",
            "transport": "Many FQHCs provide transportation assistance or telehealth options.",
        },
    },
    {
        "name":        "NAMI Helpline & Peer Support",
        "description": "Free mental health information, peer support groups, and community education "
                       "from the National Alliance on Mental Illness.",
        "cost_badge":  "free",
        "tags":        ["peer", "therapy"],
        "barriers":    ["cost", "info", "privacy"],
        "access_modes":["phone", "text", "video"],
        "links": [
            {"label": "Call NAMI",  "url": "tel:18006264673",       "icon": "ti-phone",         "primary": True},
            {"label": "Text NAMI",  "url": "sms:741741?body=NAMI",  "icon": "ti-message",       "primary": False},
            {"label": "Visit site", "url": "https://www.nami.org/help", "icon": "ti-external-link","primary": False},
        ],
        "why_text": {
            "cost":    "Entirely free — NAMI runs on donations and public funding.",
            "info":    "Helpline staff help you figure out what support you need and where to find it.",
            "privacy": "Non-judgmental and anonymous — no records kept.",
        },
    },
    {
        "name":        "Open Path Collective",
        "description": "Sliding-scale therapy ($30–$80/session) with licensed therapists across the US. "
                       "Large telehealth network with fast match times.",
        "cost_badge":  "low",
        "tags":        ["therapy", "medication"],
        "barriers":    ["cost", "waittime"],
        "access_modes":["video", "inperson"],
        "links": [
            {"label": "Find a therapist", "url": "https://openpathcollective.org", "icon": "ti-external-link", "primary": True},
        ],
        "why_text": {
            "cost":     "Sessions well below market rate — specifically for people without insurance or on limited income.",
            "waittime": "Large network means faster match times than traditional providers.",
        },
    },
    {
        "name":        "BetterHelp Online Therapy",
        "description": "App-based therapy with licensed counselors. Financial aid available. "
                       "Typical match time under 48 hours.",
        "cost_badge":  "low",
        "tags":        ["therapy"],
        "barriers":    ["transport", "waittime", "privacy"],
        "access_modes":["video", "phone", "text"],
        "links": [
            {"label": "Visit BetterHelp", "url": "https://www.betterhelp.com", "icon": "ti-external-link", "primary": True},
        ],
        "why_text": {
            "transport": "100% remote — access from your phone or computer anywhere.",
            "waittime":  "Typical match time under 48 hours vs. weeks for traditional therapy.",
            "privacy":   "Anonymous messaging option available — your name is optional.",
        },
    },
    {
        "name":        "SAMHSA Treatment Locator",
        "description": "Search over 14,000 accredited substance use and mental health treatment "
                       "facilities by ZIP code, insurance type, and service needed.",
        "cost_badge":  "free",
        "tags":        ["substance", "medication", "therapy"],
        "barriers":    ["info", "cost"],
        "access_modes":["inperson", "phone"],
        "links": [
            {"label": "Search by ZIP",  "url": "https://findtreatment.gov",  "icon": "ti-map-pin",   "primary": True},
            {"label": "Call helpline",  "url": "tel:18006624357",             "icon": "ti-phone",     "primary": False},
        ],
        "why_text": {
            "info": "The most comprehensive public directory of US treatment facilities — filters by insurance and service type.",
            "cost": "Includes filters for sliding-scale and free programs.",
        },
    },
    {
        "name":        "SMART Recovery",
        "description": "Free, science-based peer support groups for addiction and recovery. "
                       "Online meetings available every day of the week.",
        "cost_badge":  "free",
        "tags":        ["substance", "peer"],
        "barriers":    ["cost", "transport", "privacy"],
        "access_modes":["video", "phone", "text"],
        "links": [
            {"label": "Find a meeting", "url": "https://www.smartrecovery.org/community/calendar.php", "icon": "ti-calendar",      "primary": True},
            {"label": "Visit site",     "url": "https://www.smartrecovery.org",                        "icon": "ti-external-link", "primary": False},
        ],
        "why_text": {
            "cost":      "All meetings are free — no dues, no 12-step requirement.",
            "transport": "Online daily meetings mean no commute.",
            "privacy":   "Participate anonymously with camera off.",
        },
    },
    {
        "name":        "Psychology Today Therapist Finder",
        "description": "Search therapists by specialty, insurance, language, and sliding-scale "
                       "availability. Includes real-time telehealth availability.",
        "cost_badge":  "low",
        "tags":        ["therapy", "medication"],
        "barriers":    ["language", "info", "waittime"],
        "access_modes":["inperson", "video", "phone"],
        "links": [
            {"label": "Find a therapist", "url": "https://www.psychologytoday.com/us/therapists", "icon": "ti-external-link", "primary": True},
        ],
        "why_text": {
            "language": "Filter by therapist language — 40+ languages listed.",
            "info":     "Detailed profiles explain each therapist's approach so you can make an informed choice.",
            "waittime": "Shows real-time availability calendars — find who has openings this week.",
        },
    },
    {
        "name":        "Crisis Text Line",
        "description": "Free 24/7 crisis support via text message. Text HOME to 741741 from any phone. "
                       "No call required — ideal for private or quiet situations.",
        "cost_badge":  "free",
        "tags":        ["crisis", "peer"],
        "barriers":    ["privacy", "cost", "info"],
        "access_modes":["text"],
        "links": [
            {"label": "Text HOME to 741741", "url": "sms:741741?body=HOME", "icon": "ti-message", "primary": True},
            {"label": "Visit site",          "url": "https://www.crisistextline.org", "icon": "ti-external-link", "primary": False},
        ],
        "why_text": {
            "privacy": "Text-only — no voice call required. Usable in private or quiet situations.",
            "cost":    "Completely free from any mobile phone.",
            "info":    "Crisis counselors can help you identify local resources in real time.",
        },
    },
    {
        "name":        "Trevor Project",
        "description": "Crisis intervention and suicide prevention for LGBTQ+ young people. "
                       "Free, confidential, 24/7 support by phone, text, or chat.",
        "cost_badge":  "free",
        "tags":        ["crisis", "peer"],
        "barriers":    ["privacy", "cost", "info"],
        "access_modes":["phone", "text", "video"],
        "links": [
            {"label": "Call TrevorLifeline", "url": "tel:18664887386",          "icon": "ti-phone",         "primary": True},
            {"label": "Text START to 678678","url": "sms:678678?body=START",    "icon": "ti-message",       "primary": False},
            {"label": "TrevorChat",          "url": "https://www.thetrevorproject.org/get-help/", "icon": "ti-external-link", "primary": False},
        ],
        "why_text": {
            "privacy": "Confidential support specifically for LGBTQ+ youth — trained counselors understand your situation.",
            "cost":    "Completely free.",
            "info":    "Can connect you with local and national LGBTQ+-affirming resources.",
        },
    },
    {
        "name":        "MentalHealth.gov Resource Locator",
        "description": "Official US government directory of local mental health services, "
                       "hotlines, and treatment options. Filter by state and service type.",
        "cost_badge":  "free",
        "tags":        ["therapy", "peer", "medication", "substance"],
        "barriers":    ["info"],
        "access_modes":["inperson", "phone", "video"],
        "links": [
            {"label": "Find local help", "url": "https://www.mentalhealth.gov/get-help/immediate-help", "icon": "ti-external-link", "primary": True},
        ],
        "why_text": {
            "info": "Official US government resource — comprehensive directory organized by need and location.",
        },
    },
]


def seed():
    db = SessionLocal()
    try:
        existing = db.query(models.Resource).count()
        if existing > 0:
            print(f"Database already has {existing} resources. Skipping seed.")
            print("To re-seed, delete bridgecheck.db and run again.")
            return

        for data in RESOURCES:
            resource = models.Resource(**data)
            db.add(resource)

        db.commit()
        print(f"✓ Seeded {len(RESOURCES)} resources into the database.")
    except Exception as e:
        db.rollback()
        print(f"✗ Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
