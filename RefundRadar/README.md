# Refund Radar

Track. Verify. Get Your Money Back.

A clean rebuild of Refund Radar: FastAPI + Supabase backend, vanilla
HTML/CSS/JS frontend, rule-based explainable risk scoring.

## 1. Database setup (do this first)

1. Open your Supabase project → **SQL Editor** → New query.
2. Paste the contents of `sql/schema.sql` and run it.
   This drops and recreates `transactions`, `refunds`, `evidence` with
   proper constraints, and creates the private `evidence` storage bucket.
   (Your old project's tables were missing several columns and had no
   constraints — that's what caused the `null`/`[object Object]` bugs.)

## 2. Backend

```bash
cd Backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The `.env` file already has your Supabase project's URL and secret key.
API runs at `http://127.0.0.1:8000` — visit `/docs` for interactive API docs.

Optional sanity check (no real DB needed, uses an in-memory fake):

```bash
python3 tests_mock_smoke.py
```

## 3. Frontend

Any static file server works. Easiest options:

```bash
cd Frontend
python3 -m http.server 5500
# then open http://127.0.0.1:5500
```

...or open `Frontend/index.html` with VS Code's "Live Server" extension.

The frontend talks only to your FastAPI backend (`API_BASE` in
`Frontend/js/config.js`) — it never talks to Supabase directly, so your
secret key is never exposed to the browser.

## Project structure

```
Backend/
  app/
    main.py              FastAPI app, CORS, global error handling
    constants.py          shared enums (statuses, platforms, evidence types)
    supabase_client.py    single Supabase client (service_role key)
    api/
      transactions.py
      refunds.py
      evidence.py
      dashboard.py
    services/
      risk_engine.py       rule-based, explainable risk scoring
Frontend/
  index.html               all views (splash, dashboard, transactions, ...)
  css/style.css
  js/
    config.js               API base URL, labels, formatters
    api.js                  fetch wrapper + friendly error messages + toasts
    state.js                data loading (correct order) + global state
    render.js               all rendering, reads only from state
    forms.js                add/edit forms, modals, evidence upload
    app.js                  init + navigation
sql/schema.sql              run once in Supabase SQL Editor
```

## Notes

- No hardcoded numbers anywhere in the frontend — every figure on the
  dashboard comes from `GET /dashboard/summary` and `/dashboard/risk-summary`.
- The risk engine is a simple, transparent points system (see
  `app/services/risk_engine.py`) — not an ML prediction — and every score
  comes with a plain-English list of reasons.
- No SMS/email/push notifications anywhere. "Alerts" is an in-app view
  computed from your own overdue/due-soon/high-risk refunds.
