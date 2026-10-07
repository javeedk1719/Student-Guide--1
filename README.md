# 🎓 Student Guide

An EdTech platform for college students: AI-generated learning roadmaps, YouTube resources for every topic,
daily tasks, explained tech news, a college community and progress tracking.

**Stack:** Python · FastAPI · Pydantic · SQLAlchemy · Supabase PostgreSQL · HTML/CSS/JavaScript ·
Groq API · YouTube Data API · NewsAPI

---

## 1. Run it locally

```bash
python -m venv venv
venv\Scripts\activate          # Windows      (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt

cp .env.example .env           # Windows: copy .env.example .env
# open .env and fill in the values (see section 2)

uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>. Swagger docs are at <http://127.0.0.1:8000/docs>.
Tables are created automatically on startup.

Run the tests (they use a temporary SQLite file and mock Groq, so no keys needed):

```bash
pytest -q
```

## 2. Environment variables (`.env`)

| Variable | Where to get it |
|---|---|
| `DATABASE_URL` | Supabase → Project Settings → Database → Connection string → URI. Replace `[YOUR-PASSWORD]`. Use the **pooler** URL if your network is IPv4-only. |
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `GROQ_API_KEY` | <https://console.groq.com/keys> |
| `YOUTUBE_API_KEY` | Google Cloud Console → enable *YouTube Data API v3* → Credentials → API key |
| `NEWS_API_KEY` | <https://newsapi.org> |

Optional: `GROQ_MODEL`, `COOKIE_SECURE`, `TIMEZONE`, `NEWS_REFRESH_HOURS` (see `.env.example`).

**Never commit `.env`.** It is already in `.gitignore`. Keys exist only on the server; the browser never sees them.

For a quick local try-out without Supabase you can use `DATABASE_URL=sqlite:///./local.db`.

## 3. How it works

```text
Browser (HTML/CSS/JS)  ->  FastAPI router  ->  service  ->  Groq / YouTube / NewsAPI
                                   |
                              SQLAlchemy  ->  Supabase PostgreSQL
```

```text
app/
  main.py             app setup, routers, security headers
  config.py           reads .env once
  database/           engine + all SQLAlchemy models
  schemas/            Pydantic request/response models
  auth/               password hashing, JWT, get_current_user
  routers/            HTTP endpoints (thin)
  services/           groq / youtube / news / roadmap / task logic
templates/ static/    the frontend pages, CSS and JS
tests/                smoke tests
```

### Database tables
`users`, `roadmaps`, `roadmap_steps`, `resources`, `step_resources` (link table), `progress`,
`resource_completions`, `daily_tasks`, `task_completions`, `tech_updates`, `community_profiles`, `community_posts`.

### Main flows
- **Roadmap:** `POST /api/roadmap/generate` asks Groq for JSON, validates it with Pydantic, saves steps + progress rows.
- **Resources:** a step's videos are searched on YouTube the first time you open them, then saved and reused (saves quota).
- **Daily task:** one per user per day. Generated once by Groq (falls back to your roadmap's practice task if the AI is down), then reused.
- **Tech updates:** NewsAPI articles are fetched at most every 3 hours, explained in one batched Groq call and stored.
- **Community:** discover people at your college (senior/junior/peer is derived from year of study) and post questions, resources, project ideas.

### API summary
```text
POST /api/auth/register | login | logout        GET /api/auth/me
GET/PUT /api/profile                             GET /api/roles
POST /api/roadmap/generate    GET /api/roadmap    GET /api/roadmap/{id}    GET /api/roadmap/{id}/steps
POST /api/roadmap/steps/{id}/complete             GET /api/roadmap/steps/{id}/resources
GET /api/resources/search?query=   GET /api/resources/{id}   POST /api/resources/{id}/complete
GET /api/tech-updates[?role=]      GET /api/tech-updates/{id}
GET /api/tasks/today   GET /api/tasks   POST /api/tasks/{id}/complete
GET /api/progress
GET /api/community/users   GET/POST /api/community/posts   DELETE /api/community/posts/{id}
```

## 4. Security notes
- Passwords are hashed with bcrypt; plaintext is never stored or logged.
- Login sets an **HttpOnly, SameSite=Lax** cookie holding a signed JWT (the Authorization: Bearer header also works for API tools).
- Every private query filters by the logged-in user's id; other users' ids return 404.
- All input is validated by Pydantic. The frontend escapes all server data before rendering (XSS) and a strict
  Content-Security-Policy blocks inline scripts.
- API keys are read only in `config.py` and never returned by any endpoint. Error messages never include keys.
- Not included (add if you have time): login rate limiting, email verification, password reset.

## 5. Deploying (e.g. Render / Railway)
1. Push to GitHub (check `.env` is **not** in the repo).
2. Build command: `pip install -r requirements.txt`
3. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add the environment variables in the host's dashboard and set `COOKIE_SECURE=true` (HTTPS).

## 6. Troubleshooting
- **`SECRET_KEY is too short`** → generate a real key (section 2).
- **Database connection errors** → check the password in `DATABASE_URL`; try the Supabase pooler URL.
- **Roadmap generation fails with status 400/404 from the AI** → the Groq model name may have changed; set `GROQ_MODEL` to a current model from the Groq console.
- **YouTube 403** → API not enabled for the key, or daily quota (100 searches/day on the free tier) used up.
- **No news** → NewsAPI's free plan delays articles by 24 hours and limits requests per day.
