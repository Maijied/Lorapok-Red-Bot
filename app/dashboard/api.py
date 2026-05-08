from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.dashboard.metrics import metrics_store
from app.moderation.memory import recent_cases
from app.moderation.queue import list_queue, resolve_case

app = FastAPI(title="Lorapok Red Bot Dashboard")


class ReviewResolutionRequest(BaseModel):
    status: str = Field(pattern="^(approved|rejected|escalated)$")
    reviewer_note: str = ""


_DASHBOARD_HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Lorapok Red Bot Dashboard</title>
    <style>
      :root {
        --bg: #0e1016;
        --panel: #171a23;
        --panel-soft: #1d2130;
        --text: #e9eef8;
        --text-dim: #aab3c7;
        --primary: #ff2f55;
        --primary-soft: #ff6d86;
        --border: #2a3042;
        --good: #23c879;
        --warn: #f2b448;
      }
      * {
        box-sizing: border-box;
      }
      body {
        margin: 0;
        font-family: Inter, "Segoe UI", Roboto, sans-serif;
        color: var(--text);
        background: radial-gradient(circle at top right, #2a0e1a 0%, var(--bg) 38%);
      }
      .wrap {
        max-width: 1160px;
        margin: 0 auto;
        padding: 24px;
      }
      .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 16px;
        margin-bottom: 20px;
      }
      .title {
        margin: 0;
        font-size: 1.6rem;
        letter-spacing: 0.3px;
      }
      .subtitle {
        margin: 6px 0 0;
        color: var(--text-dim);
        font-size: 0.95rem;
      }
      .pill {
        border: 1px solid var(--border);
        border-radius: 999px;
        padding: 8px 14px;
        background: var(--panel);
        color: var(--text-dim);
        font-size: 0.86rem;
      }
      .grid {
        display: grid;
        gap: 14px;
        grid-template-columns: repeat(4, minmax(0, 1fr));
      }
      .card {
        background: linear-gradient(180deg, var(--panel-soft), var(--panel));
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 14px;
      }
      .metric-title {
        color: var(--text-dim);
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.07em;
      }
      .metric-value {
        margin-top: 8px;
        font-size: 1.8rem;
        font-weight: 700;
      }
      .section {
        margin-top: 14px;
      }
      .section h2 {
        margin: 0 0 10px;
        font-size: 1.1rem;
      }
      .table-wrap {
        overflow-x: auto;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 12px;
        overflow: hidden;
      }
      th, td {
        padding: 10px 12px;
        text-align: left;
        border-bottom: 1px solid var(--border);
        vertical-align: top;
      }
      th {
        color: var(--text-dim);
        font-weight: 600;
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
      }
      tr:last-child td {
        border-bottom: none;
      }
      .status {
        display: inline-block;
        border-radius: 999px;
        padding: 2px 10px;
        font-size: 0.76rem;
        font-weight: 600;
      }
      .status-ok {
        background: rgba(35, 200, 121, 0.18);
        color: var(--good);
      }
      .status-pending {
        background: rgba(242, 180, 72, 0.18);
        color: var(--warn);
      }
      button, select, input {
        background: #111524;
        color: var(--text);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 7px 10px;
      }
      button {
        background: linear-gradient(180deg, var(--primary-soft), var(--primary));
        border: none;
        color: white;
        cursor: pointer;
        font-weight: 600;
      }
      button:hover {
        filter: brightness(1.06);
      }
      .inline-actions {
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
      }
      .muted {
        color: var(--text-dim);
      }
      @media (max-width: 960px) {
        .grid {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }
      }
      @media (max-width: 640px) {
        .grid {
          grid-template-columns: 1fr;
        }
      }
    </style>
  </head>
  <body>
    <main class="wrap">
      <div class="header">
        <div>
          <h1 class="title">Lorapok Red Bot · Moderator Dashboard</h1>
          <p class="subtitle">
            Professional moderation visibility and review workflow for developer communities.
          </p>
        </div>
        <div id="healthPill" class="pill">Status: checking…</div>
      </div>
      <section class="grid">
        <article class="card">
          <div class="metric-title">Comments Processed</div>
          <div class="metric-value" id="commentsProcessed">0</div>
        </article>
        <article class="card">
          <div class="metric-title">Actions Taken</div>
          <div class="metric-value" id="actionsTaken">0</div>
        </article>
        <article class="card">
          <div class="metric-title">Queued Reviews</div>
          <div class="metric-value" id="queuedReviews">0</div>
        </article>
        <article class="card">
          <div class="metric-title">Posts Processed</div>
          <div class="metric-value" id="postsProcessed">0</div>
        </article>
      </section>
      <section class="section">
        <h2>Pending Review Queue</h2>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Case</th>
                <th>Reason</th>
                <th>Source</th>
                <th>Created</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody id="reviewRows">
              <tr><td colspan="5" class="muted">No pending reviews.</td></tr>
            </tbody>
          </table>
        </div>
      </section>
      <section class="section">
        <h2>Recent Memory Cases</h2>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Text Hash</th>
                <th>Action</th>
                <th>Reason</th>
                <th>Source</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody id="memoryRows">
              <tr><td colspan="5" class="muted">No memory entries yet.</td></tr>
            </tbody>
          </table>
        </div>
      </section>
    </main>
    <script>
      async function fetchJson(path) {
        const response = await fetch(path);
        if (!response.ok) throw new Error(`Request failed: ${path}`);
        return response.json();
      }

      function renderReviews(pending) {
        const tbody = document.getElementById("reviewRows");
        if (!pending.length) {
          tbody.innerHTML = '<tr><td colspan="5" class="muted">No pending reviews.</td></tr>';
          return;
        }
        tbody.innerHTML = pending.map((item) => `
          <tr>
            <td>
              <div><strong>${item.case_id}</strong></div>
              <div class="muted">${(item.text || "").slice(0, 90)}</div>
            </td>
            <td>${item.reason || ""}</td>
            <td>${item.source || ""}</td>
            <td>${item.created_at || ""}</td>
            <td>
              <div class="inline-actions">
                <select id="status-${item.case_id}">
                  <option value="approved">Approve</option>
                  <option value="rejected">Reject</option>
                  <option value="escalated">Escalate</option>
                </select>
                <input id="note-${item.case_id}" placeholder="note" />
                <button onclick="resolveReview('${item.case_id}')">Apply</button>
              </div>
            </td>
          </tr>
        `).join("");
      }

      function renderMemory(recent) {
        const tbody = document.getElementById("memoryRows");
        if (!recent.length) {
          tbody.innerHTML = '<tr><td colspan="5" class="muted">No memory entries yet.</td></tr>';
          return;
        }
        tbody.innerHTML = recent.map((item) => `
          <tr>
            <td>${item.text_hash || ""}</td>
            <td>${item.action || ""}</td>
            <td>${item.reason || ""}</td>
            <td>${item.source || ""}</td>
            <td>${item.created_at || ""}</td>
          </tr>
        `).join("");
      }

      async function resolveReview(caseId) {
        const status = document.getElementById(`status-${caseId}`).value;
        const reviewerNote = document.getElementById(`note-${caseId}`).value;
        await fetch(`/reviews/${caseId}/resolve`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status, reviewer_note: reviewerNote }),
        });
        await refreshDashboard();
      }

      async function refreshDashboard() {
        try {
          const [health, metrics, reviews, memory] = await Promise.all([
            fetchJson("/health"),
            fetchJson("/metrics"),
            fetchJson("/reviews"),
            fetchJson("/memory"),
          ]);

          const healthPill = document.getElementById("healthPill");
          healthPill.textContent = `Status: ${health.status}`;
          healthPill.classList.add("status-ok");

          document.getElementById("commentsProcessed").textContent =
            metrics.comments_processed ?? 0;
          document.getElementById("actionsTaken").textContent = metrics.actions_taken ?? 0;
          document.getElementById("queuedReviews").textContent = metrics.queued_reviews ?? 0;
          document.getElementById("postsProcessed").textContent = metrics.posts_processed ?? 0;

          renderReviews(reviews.pending || []);
          renderMemory(memory.recent || []);
        } catch (error) {
          document.getElementById("healthPill").textContent = "Status: unavailable";
          console.error(error);
        }
      }

      refreshDashboard();
      setInterval(refreshDashboard, 8000);
    </script>
  </body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return _DASHBOARD_HTML


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> dict[str, int]:
    base = {
        "posts_processed": 0,
        "comments_processed": 0,
        "queued_reviews": 0,
        "actions_taken": 0,
    }
    base.update(metrics_store.snapshot())
    return base


@app.get("/reviews")
def reviews() -> dict[str, list[dict[str, str]]]:
    return {"pending": list_queue(status="pending")}

@app.post("/reviews/{case_id}/resolve")
def resolve_review(case_id: str, payload: ReviewResolutionRequest) -> dict[str, Any]:
    updated = resolve_case(case_id, payload.status, payload.reviewer_note)
    if not updated:
        raise HTTPException(status_code=400, detail="Unable to resolve review case.")
    return {"ok": True, "pending": list_queue(status="pending")}


@app.get("/memory")
def memory() -> dict[str, list[dict[str, str]]]:
    return {"recent": recent_cases()}
