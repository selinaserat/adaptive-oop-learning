# Adaptive OOP Learning backend

Flask API for students, lessons, diagnostic assessments, server-side quiz scoring, mastery, prerequisites, recommendations, progress, and attempt history. The starter curriculum preserves the original three topics and six questions.

## Local setup (macOS / PyCharm)

Use the existing `.venv` as the PyCharm project interpreter. From the project directory:

```sh
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python run.py
```

Visit `http://127.0.0.1:5000/api/health`. Stop with Control-C. Run tests with `python -m pytest -q`. `python backend.py` remains a compatibility launch command. Old unprefixed URLs have been replaced by `/api`.

`.env.example` documents configuration. Flask does not automatically load `.env` in this project: set variables in PyCharm Run Configuration or your shell, for example:

```sh
export PORT=5000
export FRONTEND_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
python run.py
```

Memory storage resets on restart and is isolated per process. Use one worker for any local Gunicorn smoke test. This is a working backend with temporary storage, not yet a publicly deployable student system.

## Architecture and file guide

| File | Purpose |
|---|---|
| run.py | Creates Flask app; WSGI entry point and environment-based local launcher. |
| backend.py | Compatibility launcher replacing the original monolithic implementation. |
| app/__init__.py | Application factory, repository injection, CORS, request size limit, JSON error handlers, production storage guard. |
| app/routes/health.py | Health endpoint. |
| app/routes/topics.py | Curriculum, lessons, quiz and diagnostic retrieval. |
| app/routes/students.py | Student, dashboard, progress, attempts and submission endpoints; delegates decisions to the service. |
| app/services/learning_service.py | Validation, scoring, mastery retention, prerequisites, recommendations, atomic assessment orchestration and curriculum graph validation. |
| app/repositories/base.py | Typed repository protocol that both storage adapters must satisfy. |
| app/repositories/memory_repository.py | Detached in-memory records, thread-safe write transactions and rollback, local development storage. |
| app/repositories/sql_repository.py | Explicit integration seam awaiting the team's schema; constructor raises until implemented. |
| app/models/domain.py | Progress dataclass and allowed topic states. |
| app/data/mock_data.py | Original curriculum and private answer keys, plus starter lesson text. |
| Package __init__.py files | Establish Python packages; no business logic. |
| tests/test_api.py | API behavior, thresholds, error handling, CORS, answer secrecy, rollback and production guard tests. |
| pytest.ini | Test discovery and project import configuration. |
| requirements.txt | Flask, Flask-CORS and Gunicorn runtime dependency ranges. |
| requirements-dev.txt | Runtime dependencies plus pytest. |
| gunicorn.conf.py | Environment-based binding, one worker/four threads, timeouts, stdout logs. |
| Procfile | Hosting launch command, gunicorn run:app; auto-loads gunicorn.conf.py. |
| .env.example | Non-secret configuration examples. |
| .gitignore | Excludes virtualenv, IDE files, secrets, caches and local databases. |
| docs/API.md | Complete frontend request/response, scoring, workflow and error contract. |
| docs/DATABASE.md | Repository integration contract, logical schema and SQL teammate handoff. |
| notebook.ipynb | Existing empty notebook, unused by the backend; safe to remove if desired. |

Routes handle HTTP; the service owns learning decisions; repositories own storage. The repository transaction boundary keeps attempt records and progress consistent and lets a SQL adapter replace memory without rewriting API or business logic. Public serialization uses explicit field allowlists so answer keys cannot leak through data retrieval.

## Frontend teammate handoff

Read `docs/API.md`. Provide the frontend repository/build instructions, framework, development and final hosting origins, environments/base URL variable name, intended dashboard and diagnostic/quiz flow, agreed lesson content format, error/loading/disabled-submission behavior, and login/session design. Use IDs from API data, complete the diagnostic first, display server scores/mastery, and handle 403 responses. Configure the actual origins in FRONTEND_ORIGINS. No credentials are supported by CORS yet.

## Production preparation and remaining gates

Gunicorn is included and `gunicorn run:app` binds to PORT (default 5000) via gunicorn.conf.py. Flask debug mode is off. Production environment must set APP_ENV=production and explicit FRONTEND_ORIGINS. Startup deliberately refuses MemoryRepository. Integrate SQL first as described in docs/DATABASE.md; there is no silent fallback to ephemeral storage.

Before public student use, implement and test authentication/authorization so users can only access their own student records, agree on rate limiting and privacy/retention, replace or review the starter teaching content, and verify the SQL adapter under concurrent requests and restarts. Select the hosting provider, configure secret environment variables and TLS, run migrations/seeds, lock tested dependency versions for the deployment, and test readiness against the database. `/api/health` currently checks the running API process only, not database connectivity. Increase Gunicorn workers only after shared durable storage is connected.

No deployment, domain, or DNS changes are performed by this project setup.

## Flask website preview

Open http://127.0.0.1:5000/ after starting run.py. Flask serves app/templates/index.html with app/static/studio.css and studio.js. The website creates student profiles, submits diagnostics/quizzes, and displays lessons, recommendations, progress and recent attempts through the existing API. It uses no build tools. Student selection stays in the current page session; refresh starts a new profile flow. The API remains available for the separate frontend teammate.
