# SQLGuard Lab — SQL Injection Prevention

A standalone educational web app that demonstrates secure SQL queries with Python, Flask, and SQLite. It is a working implementation of this repository's original SQL injection prevention idea. The app uses fictional sample data and never executes an intentionally vulnerable query.

## What it shows

- A browser based catalog search with normal and injection shaped examples.
- Parameter binding (`?`) so user text cannot become SQL syntax.
- Literal `LIKE` search: `%`, `_`, and `\\` are escaped before binding.
- Request validation, a size cap, security response headers, safe DOM rendering, basic logging, and a local request limit.
- A health endpoint and tests covering normal input, injection strings, validation, and headers.

## Run locally on Ubuntu

```bash
git clone https://github.com/suryathe44/SQL-Injection-Prevention-Project.git
cd SQL-Injection-Prevention-Project
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`. The app creates a SQLite database at `/tmp/sqlguard-lab.db`. Set `DATABASE_PATH` to another writable path if needed.

## Test

```bash
python -m unittest discover -s tests -v
```

For a quick API check:

```bash
curl -s http://127.0.0.1:5000/api/search \
  -H 'Content-Type: application/json' \
  -d '{"term":"SQL"}'
```

Try `{"term":"' OR 1=1 --"}` to see that the search returns zero matches rather than changing the query.

## Run as a service

```bash
gunicorn --bind 0.0.0.0:8000 --workers 1 app:app
```

`GET /health` is available for health checks. This small demo uses SQLite and an in-memory rate limit, so use one worker and one instance. Before scaling to multiple workers or exposing a larger service, move the rate limit to a shared store or edge gateway and use a managed database. Set `DATABASE_PATH` to persistent storage if you need records to survive restarts. The seeded catalog is fictional and public; no account or personal data is stored.

## Security model

The key protection is parameter binding. Input validation and a request limit are additional controls; they do not replace bound SQL parameters. The app never displays raw SQL errors to visitors and uses `textContent` when rendering results. Injection samples are treated as data only.
