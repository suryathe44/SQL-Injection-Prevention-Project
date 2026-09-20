"""SQLGuard Lab: safe, small SQL injection prevention demonstrator."""

from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path
from time import monotonic

from flask import Flask, jsonify, render_template, request

SAMPLE_PRODUCTS = (
    (1, "Secure Login", "Authentication", "Learn safe sign-in patterns."),
    (2, "SQL Fundamentals", "Databases", "Understand relational queries."),
    (3, "Parameter Binding", "Databases", "Keep user values separate from SQL."),
    (4, "Input Validation", "Application Security", "Check data before using it."),
    (5, "Threat Modeling", "Application Security", "Map threats and trust boundaries."),
    (6, "Access Control", "Authentication", "Give users only the access they need."),
)


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        DATABASE=os.environ.get("DATABASE_PATH", "/tmp/sqlguard-lab.db"),
        MAX_CONTENT_LENGTH=4096,
        RATE_LIMIT=30,
        RATE_WINDOW=60,
    )
    if test_config:
        app.config.update(test_config)

    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    database = Path(app.config["DATABASE"])
    database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL, description TEXT NOT NULL)"
        )
        connection.executemany(
            "INSERT OR IGNORE INTO products (id, name, category, description) VALUES (?, ?, ?, ?)",
            SAMPLE_PRODUCTS,
        )

    # This local limit is a convenience guard. Use an edge or shared-store limit
    # when running multiple workers or instances.
    recent: dict[str, list[float]] = {}

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.post("/api/search")
    def search():
        client = request.remote_addr or "unknown"
        now = monotonic()
        hits = [stamp for stamp in recent.get(client, []) if now - stamp < app.config["RATE_WINDOW"]]
        if len(hits) >= app.config["RATE_LIMIT"]:
            return jsonify(error="Too many requests. Please try again shortly."), 429
        hits.append(now)
        recent[client] = hits

        if not request.is_json:
            return jsonify(error="Send JSON with a search term."), 415
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or not isinstance(payload.get("term"), str):
            return jsonify(error="Search term must be text."), 400
        term = payload["term"].strip()
        if not 1 <= len(term) <= 80:
            return jsonify(error="Search term must be 1 to 80 characters."), 400
        if any(ord(char) < 32 for char in term):
            return jsonify(error="Search term contains unsupported characters."), 400

        # Every character in `term` is data; it never becomes SQL syntax.
        with sqlite3.connect(database) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT name, category, description FROM products WHERE name LIKE ? ESCAPE '\\' ORDER BY name LIMIT 10",
                (f"%{escape_like(term)}%",),
            ).fetchall()
        app.logger.info("search completed; length=%d results=%d", len(term), len(rows))
        return jsonify(
            results=[dict(row) for row in rows],
            count=len(rows),
            query="SELECT ... FROM products WHERE name LIKE ? ESCAPE '\\'",
            explanation="The search term is bound as a value. SQL operators inside it cannot change the query.",
        )

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify(error="Request is too large."), 413

    return app


def escape_like(value: str) -> str:
    """Treat LIKE wildcards as literal user text."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
