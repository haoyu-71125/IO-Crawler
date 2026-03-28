import asyncio
import threading
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template

import database as db
from crawler import scrape_internships

app = Flask(__name__)

# ── Shared state (protected by a simple lock) ──────────────────────────────────
_state = {
    "running":   False,
    "results":   [],
    "count":     0,
    "last_run":  None,
    "error":     None,
}
_lock = threading.Lock()


def _run_crawl():
    with _lock:
        _state["running"] = True
        _state["error"]   = None

    try:
        jobs = asyncio.run(scrape_internships())
        db.upsert_jobs(jobs)
        recent = db.get_recent_jobs(hours=48)
        with _lock:
            _state["results"]  = recent
            _state["count"]    = len(recent)
            _state["last_run"] = datetime.now(timezone.utc).isoformat()
    except Exception as exc:
        with _lock:
            _state["error"] = str(exc)
    finally:
        with _lock:
            _state["running"] = False


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/run", methods=["POST"])
def api_run():
    with _lock:
        if _state["running"]:
            return jsonify({"status": "already_running"}), 409
    t = threading.Thread(target=_run_crawl, daemon=True)
    t.start()
    return jsonify({"status": "started"})


@app.route("/api/status")
def api_status():
    with _lock:
        return jsonify({
            "running":  _state["running"],
            "results":  _state["results"],
            "count":    _state["count"],
            "last_run": _state["last_run"],
            "error":    _state["error"],
        })


# Initialize database on startup
db.init_db()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting IO Crawler at http://localhost:{port}")
    app.run(debug=False, port=port, host="0.0.0.0")
