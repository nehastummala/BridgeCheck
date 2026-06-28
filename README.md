# BridgeCheck — Backend

**BridgeLogic™ Adaptive Barrier-Aware Decision Engine**  
FastAPI + SQLAlchemy + SQLite (dev) / PostgreSQL (prod)

---

## Project structure

```
bridgecheck/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py        ← FastAPI app + all routes
│   │   ├── engine.py      ← BridgeLogic™ decision engine
│   │   ├── models.py      ← SQLAlchemy database models
│   │   ├── schemas.py     ← Pydantic request/response schemas
│   │   └── database.py    ← DB connection + session
│   ├── seed.py            ← Seeds 11 verified resources into DB
│   ├── requirements.txt
│   └── README.md          ← you are here
└── frontend/
    └── bridgecheck.html   ← standalone frontend (deploy to Netlify)
```

---

## Local setup (5 minutes)

```bash
# 1. Go into the backend folder
cd bridgecheck/backend

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Seed the database with verified resources
python seed.py

# 5. Start the API server
uvicorn app.main:app --reload --port 8000
```

The API is now running at **http://localhost:8000**  
Interactive docs: **http://localhost:8000/docs**

---

## API endpoints

| Method | Path                       | Description                              |
|--------|----------------------------|------------------------------------------|
| GET    | `/`                        | Health check                             |
| GET    | `/api/resources`           | List all resources (debug)               |
| POST   | `/api/routing`             | Check if Q3 should be skipped            |
| POST   | `/api/adaptive-question`   | Get adaptive Q3 for a barrier set        |
| POST   | `/api/analyze`             | Run full BridgeLogic™ engine             |
| GET    | `/api/admin/stats`         | Anonymous aggregate stats (no PII)       |

---

## Example: run a full analysis

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "support_type": "therapy",
    "barriers": ["cost", "transport"],
    "adaptive_answer": "yes_virtual",
    "access_prefs": ["video", "phone"],
    "zip_code": "10001"
  }'
```

Returns: confidence score, barrier profile, ranked resources, action plan.

---

## Switching to PostgreSQL

Set the environment variable before starting:

```bash
export DATABASE_URL="postgresql://user:password@localhost/bridgecheck"
uvicorn app.main:app --reload
```

Then run `python seed.py` to populate it.

---

## Deploying to production

**Railway (recommended — free tier available)**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```
Set `DATABASE_URL` in Railway's environment variable panel.

**Render**
1. Connect your GitHub repo to render.com
2. Set build command: `pip install -r requirements.txt && python seed.py`
3. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add `DATABASE_URL` environment variable

---

## Connecting the frontend

In `bridgecheck.html`, update the API base URL:

```javascript
const API_BASE = "https://your-api-url.railway.app";  // or localhost:8000 for dev
```

Then replace the hardcoded `buildResults()` function with a `fetch` call to `/api/analyze`.

---

## Privacy

- `AssessmentLog` stores **zero PII**: no names, emails, IPs, or session IDs
- Only anonymous aggregate counts (barrier type, support type, confidence score)
- The `/api/admin/stats` endpoint returns only aggregated data
- See `privacy policy` page in the frontend for the user-facing version

---

## Adding new resources

Edit `seed.py` and add a new entry to the `RESOURCES` list. Each resource needs:

```python
{
    "name":         "Resource Name",
    "description":  "One or two sentences.",
    "cost_badge":   "free" | "low",
    "tags":         ["therapy","crisis","peer","substance","medication"],
    "barriers":     ["cost","transport","language","privacy","waittime","info"],
    "access_modes": ["inperson","video","phone","text"],
    "links":        [{"label":"...", "url":"...", "icon":"ti-...", "primary": True}],
    "why_text":     {"cost": "...", "transport": "..."},   # one entry per barrier it addresses
}
```

Delete `bridgecheck.db` and re-run `python seed.py` to reload.

---

## BridgeLogic™ scoring weights

| Barrier     | Navigation priority weight |
|-------------|---------------------------|
| cost        | 90                        |
| transport   | 75                        |
| privacy     | 68                        |
| waittime    | 60                        |
| language    | 55                        |
| info        | 45                        |

Resource scoring per match:
- Support type match: **+4**
- Barrier match: **+3** per barrier
- Access preference match: **+2** per mode
- Urgency bonus (crisis signals): **+1**

Confidence routing threshold: **75** (tune via `engine.CONFIDENCE_THRESHOLD`)
