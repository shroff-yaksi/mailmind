"""
MailMind Web Dashboard — Flask monitoring app (port 5050)
Runs alongside mailmind.py and provides a read-only view of email activity.

Usage:
    pip install flask
    python dashboard.py

Auth: Set DASHBOARD_USER and DASHBOARD_PASS in .env (defaults: admin/mailmind)
"""

import os
import sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask, render_template_string, jsonify, request, Response, redirect, url_for, session
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("DASHBOARD_SECRET", "mailmind-dashboard-secret-key-change-me")

DB_PATH = os.getenv("MAILMIND_DB", "mailmind.db")
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASS = os.getenv("DASHBOARD_PASS", "mailmind")

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if (request.form.get("username") == DASHBOARD_USER and
                request.form.get("password") == DASHBOARD_PASS):
            session["logged_in"] = True
            return redirect(url_for("index"))
        else:
            error = "Invalid credentials"
    return render_template_string(LOGIN_HTML, error=error)


@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    db = get_db()
    stats = {
        "total": db.execute("SELECT COUNT(*) FROM emails").fetchone()[0],
        "replied": db.execute("SELECT COUNT(*) FROM emails WHERE is_replied=1").fetchone()[0],
        "pending": db.execute("SELECT COUNT(*) FROM emails WHERE is_replied=0").fetchone()[0],
        "cached": db.execute("SELECT COUNT(*) FROM ai_cache").fetchone()[0],
    }
    recent = db.execute(
        "SELECT sender, subject, timestamp, is_replied, category, sentiment, priority "
        "FROM emails ORDER BY timestamp DESC LIMIT 10"
    ).fetchall()
    db.close()
    return render_template_string(INDEX_HTML, stats=stats, recent=recent)


@app.route("/emails")
@login_required
def emails():
    page = int(request.args.get("page", 1))
    per_page = 20
    offset = (page - 1) * per_page
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
    rows = db.execute(
        "SELECT id, sender, subject, timestamp, is_replied, category, sentiment, priority "
        "FROM emails ORDER BY timestamp DESC LIMIT ? OFFSET ?",
        (per_page, offset)
    ).fetchall()
    db.close()
    pages = (total + per_page - 1) // per_page
    return render_template_string(EMAILS_HTML, rows=rows, page=page, pages=pages, total=total)


@app.route("/api/status")
@login_required
def api_status():
    db = get_db()
    stats = {
        "total_emails": db.execute("SELECT COUNT(*) FROM emails").fetchone()[0],
        "replied": db.execute("SELECT COUNT(*) FROM emails WHERE is_replied=1").fetchone()[0],
        "pending": db.execute("SELECT COUNT(*) FROM emails WHERE is_replied=0").fetchone()[0],
        "cached_responses": db.execute("SELECT COUNT(*) FROM ai_cache").fetchone()[0],
        "last_email": None,
    }
    last = db.execute("SELECT timestamp FROM emails ORDER BY timestamp DESC LIMIT 1").fetchone()
    if last:
        stats["last_email"] = last[0]
    db.close()
    return jsonify({"status": "running", "timestamp": datetime.now().isoformat(), **stats})


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

_STYLE = """
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0f0f12; color: #e0e0e0; min-height: 100vh; }
  a { color: #5b8def; text-decoration: none; }
  a:hover { color: #7da8ff; }

  .navbar { background: #1a1a22; padding: 14px 28px; display: flex; align-items: center; justify-content: space-between;
            border-bottom: 1px solid #2a2a38; }
  .navbar .brand { font-size: 18px; font-weight: 700; color: #fff; letter-spacing: 0.5px; }
  .navbar .brand span { color: #5b8def; }
  .nav-links a { margin-left: 20px; font-size: 14px; }

  .container { max-width: 1100px; margin: 0 auto; padding: 30px 20px; }

  .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 30px; }
  .stat-card { background: #1a1a22; border: 1px solid #2a2a38; border-radius: 12px; padding: 20px 24px; }
  .stat-card .label { font-size: 12px; text-transform: uppercase; letter-spacing: 0.8px; color: #7a7a9a; margin-bottom: 8px; }
  .stat-card .value { font-size: 32px; font-weight: 700; color: #fff; }
  .stat-card.total .value { color: #5b8def; }
  .stat-card.replied .value { color: #3ecf8e; }
  .stat-card.pending .value { color: #f59e0b; }
  .stat-card.cached .value { color: #a78bfa; }

  h2 { font-size: 18px; font-weight: 600; margin-bottom: 16px; color: #c0c0d8; }

  table { width: 100%; border-collapse: collapse; background: #1a1a22; border-radius: 12px; overflow: hidden; }
  th { background: #22222e; color: #7a7a9a; font-size: 12px; text-transform: uppercase; letter-spacing: 0.6px;
       padding: 12px 14px; text-align: left; border-bottom: 1px solid #2a2a38; }
  td { padding: 11px 14px; font-size: 13px; border-bottom: 1px solid #1f1f2a; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: #20202c; }

  .badge { display: inline-block; padding: 3px 9px; border-radius: 20px; font-size: 11px; font-weight: 600; }
  .badge-yes  { background: rgba(62,207,142,0.15); color: #3ecf8e; }
  .badge-no   { background: rgba(245,158,11,0.15); color: #f59e0b; }
  .badge-pos  { background: rgba(91,141,239,0.15); color: #5b8def; }
  .badge-neg  { background: rgba(239,68,68,0.15);  color: #ef4444; }
  .badge-neu  { background: rgba(122,122,154,0.15); color: #9a9ac0; }
  .badge-high { background: rgba(239,68,68,0.15); color: #ef4444; }
  .badge-med  { background: rgba(245,158,11,0.15); color: #f59e0b; }
  .badge-low  { background: rgba(62,207,142,0.15); color: #3ecf8e; }

  .pager { margin-top: 20px; display: flex; gap: 10px; align-items: center; }
  .pager a, .pager span { padding: 7px 14px; border-radius: 8px; font-size: 13px; background: #1a1a22; border: 1px solid #2a2a38; }
  .pager a:hover { background: #22222e; }

  .login-wrap { min-height: 100vh; display: flex; align-items: center; justify-content: center; }
  .login-card { background: #1a1a22; border: 1px solid #2a2a38; border-radius: 16px; padding: 40px; width: 100%; max-width: 380px; }
  .login-card h1 { font-size: 22px; margin-bottom: 6px; color: #fff; }
  .login-card p  { font-size: 13px; color: #7a7a9a; margin-bottom: 28px; }
  .form-group { margin-bottom: 16px; }
  .form-group label { display: block; font-size: 12px; color: #9a9ac0; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
  .form-group input { width: 100%; background: #0f0f12; border: 1px solid #2a2a38; border-radius: 8px;
                      padding: 10px 14px; color: #e0e0e0; font-size: 14px; outline: none; }
  .form-group input:focus { border-color: #5b8def; }
  .btn { width: 100%; background: #5b8def; color: #fff; border: none; padding: 11px; border-radius: 8px;
          font-size: 14px; font-weight: 600; cursor: pointer; margin-top: 8px; }
  .btn:hover { background: #4a7de0; }
  .error { background: rgba(239,68,68,0.1); color: #ef4444; border: 1px solid rgba(239,68,68,0.2);
           border-radius: 8px; padding: 10px 14px; font-size: 13px; margin-bottom: 16px; }
</style>
"""

LOGIN_HTML = _STYLE + """
<body>
<div class="login-wrap">
  <div class="login-card">
    <h1>📬 MailMind</h1>
    <p>Dashboard — please sign in</p>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
    <form method="POST">
      <div class="form-group"><label>Username</label><input name="username" autocomplete="username" required></div>
      <div class="form-group"><label>Password</label><input name="password" type="password" autocomplete="current-password" required></div>
      <button class="btn" type="submit">Sign In</button>
    </form>
  </div>
</div>
</body>
"""

INDEX_HTML = _STYLE + """
<body>
<div class="navbar">
  <div class="brand">📬 Mail<span>Mind</span> Dashboard</div>
  <div class="nav-links">
    <a href="/">Overview</a>
    <a href="/emails">All Emails</a>
    <a href="/api/status">API</a>
    <a href="/logout">Logout</a>
  </div>
</div>
<div class="container">
  <div class="stats-grid">
    <div class="stat-card total"><div class="label">Total Processed</div><div class="value">{{ stats.total }}</div></div>
    <div class="stat-card replied"><div class="label">Replied</div><div class="value">{{ stats.replied }}</div></div>
    <div class="stat-card pending"><div class="label">Pending</div><div class="value">{{ stats.pending }}</div></div>
    <div class="stat-card cached"><div class="label">AI Cache Hits</div><div class="value">{{ stats.cached }}</div></div>
  </div>

  <h2>Recent Emails</h2>
  <table>
    <thead><tr><th>Sender</th><th>Subject</th><th>Time</th><th>Status</th><th>Category</th><th>Sentiment</th><th>Priority</th></tr></thead>
    <tbody>
    {% for row in recent %}
    <tr>
      <td>{{ row.sender }}</td>
      <td>{{ row.subject }}</td>
      <td>{{ row.timestamp[:16] if row.timestamp else '—' }}</td>
      <td>
        {% if row.is_replied %}<span class="badge badge-yes">✓ Replied</span>
        {% else %}<span class="badge badge-no">Pending</span>{% endif %}
      </td>
      <td>{{ row.category or '—' }}</td>
      <td>
        {% if row.sentiment == 'Positive' %}<span class="badge badge-pos">Positive</span>
        {% elif row.sentiment == 'Negative' %}<span class="badge badge-neg">Negative</span>
        {% else %}<span class="badge badge-neu">Neutral</span>{% endif %}
      </td>
      <td>
        {% if row.priority == 'High' %}<span class="badge badge-high">High</span>
        {% elif row.priority == 'Low' %}<span class="badge badge-low">Low</span>
        {% else %}<span class="badge badge-med">Medium</span>{% endif %}
      </td>
    </tr>
    {% else %}
    <tr><td colspan="7" style="text-align:center; color:#7a7a9a; padding:30px">No emails yet.</td></tr>
    {% endfor %}
    </tbody>
  </table>
</div>
</body>
"""

EMAILS_HTML = _STYLE + """
<body>
<div class="navbar">
  <div class="brand">📬 Mail<span>Mind</span> Dashboard</div>
  <div class="nav-links">
    <a href="/">Overview</a>
    <a href="/emails">All Emails</a>
    <a href="/api/status">API</a>
    <a href="/logout">Logout</a>
  </div>
</div>
<div class="container">
  <h2>All Emails ({{ total }} total)</h2>
  <table>
    <thead><tr><th>#</th><th>Sender</th><th>Subject</th><th>Time</th><th>Status</th><th>Category</th><th>Priority</th></tr></thead>
    <tbody>
    {% for row in rows %}
    <tr>
      <td style="color:#7a7a9a">{{ row.id }}</td>
      <td>{{ row.sender }}</td>
      <td>{{ row.subject }}</td>
      <td>{{ row.timestamp[:16] if row.timestamp else '—' }}</td>
      <td>
        {% if row.is_replied %}<span class="badge badge-yes">✓ Replied</span>
        {% else %}<span class="badge badge-no">Pending</span>{% endif %}
      </td>
      <td>{{ row.category or '—' }}</td>
      <td>
        {% if row.priority == 'High' %}<span class="badge badge-high">High</span>
        {% elif row.priority == 'Low' %}<span class="badge badge-low">Low</span>
        {% else %}<span class="badge badge-med">Medium</span>{% endif %}
      </td>
    </tr>
    {% else %}
    <tr><td colspan="7" style="text-align:center; color:#7a7a9a; padding:30px">No emails yet.</td></tr>
    {% endfor %}
    </tbody>
  </table>
  <div class="pager">
    {% if page > 1 %}<a href="/emails?page={{ page - 1 }}">← Prev</a>{% endif %}
    <span>Page {{ page }} / {{ pages }}</span>
    {% if page < pages %}<a href="/emails?page={{ page + 1 }}">Next →</a>{% endif %}
  </div>
</div>
</body>
"""


if __name__ == "__main__":
    port = int(os.getenv("DASHBOARD_PORT", 5050))
    print(f"🚀 MailMind Dashboard running at http://localhost:{port}")
    print(f"   Login: {DASHBOARD_USER} / {DASHBOARD_PASS}")
    app.run(host="0.0.0.0", port=port, debug=False)
