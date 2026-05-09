import os
from datetime import date, timedelta
from typing import Any, List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.dashboard.metrics import metrics_store
from app.dashboard.models import DailyMetric, PendingPost
from app.database import get_db
from app.moderation.memory import recent_cases
from app.moderation.queue import list_queue, resolve_case

app = FastAPI(title="Lorapok Red Bot Dashboard")

# Mount resources for the logo
if os.path.exists("resources"):
    app.mount("/static", StaticFiles(directory="resources"), name="static")


class ReviewResolutionRequest(BaseModel):
    status: str = Field(pattern="^(approved|rejected|escalated)$")
    reviewer_note: str = ""


class PostActionRequest(BaseModel):
    action: str = Field(pattern="^(approve|reject)$")


_DASHBOARD_HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Lorapok Red Bot | Labs Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=Roboto+Mono:wght@500&display=swap" 
          rel="stylesheet">
    <style>
      :root {
        --bg-deep: #050505;
        --bg-panel: rgba(20, 22, 28, 0.7);
        --accent-neon: #39ff14;
        --accent-cyber: #00f3ff;
        --accent-pulse: #ff2f55;
        --accent-reddit: #FF4500;
        --text-primary: #f8fafc;
        --text-secondary: #94a3b8;
        --border-glass: rgba(255, 255, 255, 0.08);
        --glow-green: 0 0 15px rgba(57, 255, 20, 0.3);
        --glow-reddit: 0 0 15px rgba(255, 69, 0, 0.4);
        --sidebar-width: 260px;
      }

      * { box-sizing: border-box; }

      body {
        margin: 0;
        font-family: 'Inter', sans-serif;
        background: var(--bg-deep);
        color: var(--text-primary);
        display: flex;
        height: 100vh;
        overflow: hidden;
      }

      /* Animated Background */
      .cyber-bg {
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        z-index: -1;
        background: 
          radial-gradient(circle at 80% 20%, rgba(0, 243, 255, 0.05) 0%, transparent 40%),
          radial-gradient(circle at 20% 80%, rgba(255, 69, 0, 0.05) 0%, transparent 40%);
        overflow: hidden;
      }
      .cyber-bg::after {
        content: "";
        position: absolute;
        top: 0; left: 0; width: 100%; height: 100%;
        background-image: 
          linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
        background-size: 50px 50px;
        mask-image: radial-gradient(ellipse at center, black, transparent 80%);
      }

      /* Sidebar */
      .sidebar {
        width: var(--sidebar-width);
        background: rgba(10, 11, 14, 0.95);
        border-right: 1px solid var(--border-glass);
        display: flex;
        flex-direction: column;
        padding: 32px 20px;
        z-index: 10;
        backdrop-blur: 10px;
      }

      .brand {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 48px;
        padding-left: 8px;
      }
      
      /* Reddit + Lorapok Logo Fusion */
      .logo-container {
        position: relative;
        width: 44px;
        height: 44px;
        background: var(--accent-reddit);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: var(--glow-reddit);
      }
      .logo-img {
        width: 28px;
        height: 28px;
        border-radius: 4px;
        object-fit: cover;
      }
      .logo-badge {
        position: absolute;
        bottom: -2px;
        right: -2px;
        width: 14px;
        height: 14px;
        background: var(--accent-neon);
        border: 2px solid #000;
        border-radius: 50%;
      }

      .brand-name {
        font-size: 1.1rem; font-weight: 800; letter-spacing: -0.5px;
        text-transform: uppercase;
      }
      .brand-name span { color: var(--accent-reddit); }

      .nav-group { margin-bottom: 32px; }
      .nav-label {
        font-size: 0.7rem; color: var(--text-secondary);
        text-transform: uppercase; letter-spacing: 1.5px;
        margin-bottom: 16px; padding-left: 12px;
      }
      .nav-item {
        display: flex; align-items: center; gap: 12px;
        padding: 12px 16px; border-radius: 12px;
        color: var(--text-secondary); text-decoration: none;
        font-size: 0.9rem; font-weight: 600;
        transition: all 0.2s ease; margin-bottom: 4px;
        cursor: pointer;
      }
      .nav-item:hover {
        background: rgba(255, 255, 255, 0.05);
        color: var(--text-primary);
      }
      .nav-item.active {
        border-left: 3px solid var(--accent-reddit);
        background: linear-gradient(90deg, rgba(255, 69, 0, 0.1), transparent);
        color: var(--text-primary);
      }
      .nav-item.special {
        color: var(--accent-cyber);
        border: 1px solid rgba(0, 243, 255, 0.2);
        margin-top: 12px;
      }

      /* Main Content */
      .content {
        flex: 1;
        padding: 40px;
        overflow-y: auto;
        position: relative;
      }

      .page-header {
        display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 40px;
      }
      .page-title h1 { margin: 0; font-size: 2rem; font-weight: 800; letter-spacing: -1px; }
      .page-title p { margin: 8px 0 0; color: var(--text-secondary); font-size: 0.95rem; }

      .status-badge {
        display: flex; align-items: center; gap: 8px;
        background: rgba(57, 255, 20, 0.05);
        padding: 8px 16px; border-radius: 99px;
        border: 1px solid rgba(57, 255, 20, 0.2);
        font-size: 0.8rem; font-weight: 700; color: var(--accent-neon);
      }
      .pulse-dot {
        width: 8px; height: 8px; border-radius: 50%;
        background: var(--accent-neon);
        box-shadow: 0 0 10px var(--accent-neon);
        animation: pulse 2s infinite;
      }

      @keyframes pulse {
        0% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.3); opacity: 0.5; }
        100% { transform: scale(1); opacity: 1; }
      }

      /* View Sections */
      .view-section { display: none; }
      .view-section.active { display: block; }

      /* Stats Grid */
      .stats-grid {
        display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px;
        margin-bottom: 40px;
      }
      .stat-card {
        background: var(--bg-panel);
        backdrop-filter: blur(12px);
        border: 1px solid var(--border-glass);
        padding: 24px; border-radius: 20px;
        transition: transform 0.2s ease;
      }
      .stat-card:hover { transform: translateY(-4px); border-color: rgba(255,255,255,0.15); }
      .stat-label { 
        font-size: 0.8rem; color: var(--text-secondary); 
        font-weight: 600; text-transform: uppercase; letter-spacing: 1px; 
      }
      .stat-value { 
        font-size: 2.2rem; font-weight: 800; margin-top: 12px; 
        font-family: 'Roboto Mono', monospace; 
      }

      /* Section Styling */
      .glass-section {
        background: var(--bg-panel);
        backdrop-filter: blur(12px);
        border: 1px solid var(--border-glass);
        border-radius: 24px;
        padding: 32px; margin-bottom: 32px;
      }
      .section-header {
        display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 24px;
      }
      .section-header h2 { margin: 0; font-size: 1.25rem; font-weight: 700; }

      /* Tables */
      .table-wrapper { width: 100%; overflow-x: auto; }
      table { width: 100%; border-collapse: collapse; text-align: left; }
      th {
        padding: 16px; font-size: 0.75rem; font-weight: 700;
        color: var(--text-secondary); text-transform: uppercase;
        letter-spacing: 1px; border-bottom: 1px solid var(--border-glass);
      }
      td { padding: 16px; font-size: 0.9rem; border-bottom: 1px solid var(--border-glass); }
      tr:last-child td { border-bottom: none; }
      tr:hover td { background: rgba(255,255,255,0.02); }

      /* Components */
      .btn {
        padding: 10px 20px; border-radius: 12px;
        font-size: 0.85rem; font-weight: 700; cursor: pointer;
        transition: all 0.2s ease; border: none;
      }
      .btn-primary {
        background: var(--accent-neon); color: #000;
        box-shadow: 0 4px 14px rgba(57, 255, 20, 0.3);
      }
      .btn-primary:hover { 
        transform: translateY(-2px); 
        box-shadow: 0 6px 20px rgba(57, 255, 20, 0.4); 
      }
      .btn-secondary {
        background: rgba(255,255,255,0.05); color: var(--text-primary);
        border: 1px solid var(--border-glass);
      }
      .btn-secondary:hover { background: rgba(255,255,255,0.1); }

      select, input {
        background: rgba(255,255,255,0.05); border: 1px solid var(--border-glass);
        color: var(--text-primary); padding: 10px 14px; border-radius: 10px;
        font-size: 0.85rem; outline: none;
      }
      
      .tag {
        font-family: 'Roboto Mono', monospace; font-size: 0.7rem;
        background: rgba(0, 243, 255, 0.1); color: var(--accent-cyber);
        padding: 4px 8px; border-radius: 6px;
      }

      .content-preview {
        max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        color: var(--text-secondary); font-size: 0.85rem;
      }

      /* Scrollbar */
      ::-webkit-scrollbar { width: 6px; }
      ::-webkit-scrollbar-track { background: transparent; }
      ::-webkit-scrollbar-thumb { background: var(--border-glass); border-radius: 10px; }
      ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.15); }
    </style>
  </head>
  <body>
    <div class="cyber-bg"></div>

    <aside class="sidebar">
      <div class="brand">
        <div class="logo-container">
            <img src="/static/logo-120.png" class="logo-img" alt="Fusion Logo">
            <div class="logo-badge"></div>
        </div>
        <div class="brand-name">Lorapok<span> Red Bot</span></div>
      </div>

      <div class="nav-group">
        <div class="nav-label">Management</div>
        <div class="nav-item active" onclick="switchView('overview')">Overview</div>
        <div class="nav-item" onclick="switchView('review-queue')">Review Queue</div>
        <div class="nav-item" onclick="switchView('content-drafts')">Content Drafts</div>
      </div>

      <div class="nav-group">
        <div class="nav-label">Analytics</div>
        <div class="nav-item" onclick="switchView('growth-data')">Growth Data</div>
        <div class="nav-item" onclick="switchView('ai-perf')">AI Performance</div>
      </div>

      <div class="nav-group">
        <div class="nav-label">Developer</div>
        <a href="https://github.com/your-repo/lorapok-red-bot/blob/main/docs/how_to_use.md" 
           target="_blank" class="nav-item special">
          HOW TO USE
        </a>
      </div>

      <div style="margin-top: auto; padding-left: 12px;">
        <p style="font-size: 0.7rem; color: var(--text-secondary);">Lorapok Labs Red Bot v2.0-PRO</p>
      </div>
    </aside>

    <main class="content">
      <header class="page-header">
        <div class="page-title">
          <h1 id="viewTitle">Labs Command Center</h1>
          <p id="viewSubtitle">Real-time autonomous community management system.</p>
        </div>
        <div class="status-badge">
          <div class="pulse-dot"></div>
          SYSTEM ONLINE: <span id="currentModel" style="color:white; margin-left:4px;">...</span>
        </div>
      </header>

      <div id="overview" class="view-section active">
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-label">Processed</div>
              <div class="stat-value" id="commentsProcessed">0</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">Actions</div>
              <div class="stat-value" id="actionsTaken" style="color:var(--accent-cyber)">0</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">Queued</div>
              <div class="stat-value" id="queuedReviews" style="color:var(--accent-pulse)">0</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">Published</div>
              <div class="stat-value" id="postsProcessed">0</div>
            </div>
          </div>

          <section class="glass-section">
            <div class="section-header">
              <h2>Recent Neural Memory</h2>
            </div>
            <div class="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Vector ID</th>
                    <th>Action Taken</th>
                    <th>Logic Path</th>
                    <th>Executed At</th>
                  </tr>
                </thead>
                <tbody id="memoryRowsOverview">
                </tbody>
              </table>
            </div>
          </section>
      </div>

      <div id="review-queue" class="view-section">
          <section class="glass-section">
            <div class="section-header">
              <h2>Pending Review Queue</h2>
              <span class="tag" id="reviewCount">0 CASES</span>
            </div>
            <div class="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Incident Details</th>
                    <th>Detection Reason</th>
                    <th>Signal Source</th>
                    <th>Decision</th>
                  </tr>
                </thead>
                <tbody id="reviewRows">
                  <tr>
                    <td colspan="4" style="text-align:center; color:var(--text-secondary); 
                                           padding:40px;">
                      No critical incidents detected.
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
      </div>

      <div id="content-drafts" class="view-section">
          <section class="glass-section">
            <div class="section-header">
              <h2>Content Drafts</h2>
            </div>
            <div class="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Draft Analysis</th>
                    <th>Intelligence Source</th>
                    <th>Timestamp</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody id="draftRows">
                  <tr>
                    <td colspan="4" style="text-align:center; color:var(--text-secondary); 
                                           padding:40px;">
                      No content drafts available.
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
      </div>

      <div id="growth-data" class="view-section">
          <section class="glass-section">
            <div class="section-header">
              <h2>Community Growth Data</h2>
            </div>
            <div style="padding: 40px; text-align: center; color: var(--text-secondary);">
                Analytics module initializing... 
                <br><br>
                <div style="font-family: 'Roboto Mono'; font-size: 2rem; color: var(--accent-cyber);">78%</div>
            </div>
          </section>
      </div>

      <div id="ai-perf" class="view-section">
          <section class="glass-section">
            <div class="section-header">
              <h2>AI Logic Performance</h2>
            </div>
            <div style="padding: 40px; text-align: center; color: var(--text-secondary);">
                Neural metrics are being calculated in the background.
            </div>
          </section>
      </div>

    </main>

    <script>
      function switchView(viewId) {
        // Update Nav
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
            const itemText = item.textContent.toLowerCase().replace(/ /g, '-');
            if(itemText === viewId || (viewId === 'ai-perf' && itemText === 'ai-performance') || (viewId === 'growth-data' && itemText === 'growth-data')) {
                item.classList.add('active');
            }
        });

        // Update Sections
        document.querySelectorAll('.view-section').forEach(sec => {
            sec.classList.remove('active');
        });
        document.getElementById(viewId).classList.add('active');

        // Update Header
        const titleMap = {
            'overview': 'Labs Command Center',
            'review-queue': 'Review Resolution',
            'content-drafts': 'Content Curation',
            'growth-data': 'Growth Analytics',
            'ai-perf': 'AI Performance Metrics'
        };
        document.getElementById('viewTitle').textContent = titleMap[viewId];
      }

      async function fetchJson(path) {
        const response = await fetch(path);
        if (!response.ok) throw new Error(`Request failed: ${path}`);
        return response.json();
      }

      function renderReviews(pending) {
        const tbody = document.getElementById("reviewRows");
        document.getElementById("reviewCount").textContent = `${pending.length} CASES`;
        
        if (!pending.length) {
          tbody.innerHTML = `
            <tr>
              <td colspan="4" style="text-align:center; color:var(--text-secondary); 
                                     padding:40px;">
                All clear. No pending reviews.
              </td>
            </tr>`;
          return;
        }
        tbody.innerHTML = pending.map((item) => `
          <tr>
            <td>
              <div style="font-weight:700; margin-bottom:4px;">ID: ${item.case_id}</div>
              <div class="content-preview">${item.text}</div>
            </td>
            <td><span style="color:var(--accent-pulse)">${item.reason}</span></td>
            <td><span class="tag">${item.source}</span></td>
            <td>
              <div style="display:flex; gap:8px;">
                <select id="status-${item.case_id}" style="width:120px;">
                  <option value="approved">Approve</option>
                  <option value="rejected">Reject</option>
                </select>
                <button class="btn btn-primary" 
                        onclick="resolveReview('${item.case_id}')">Apply</button>
              </div>
            </td>
          </tr>
        `).join("");
      }

      function renderDrafts(drafts) {
        const tbody = document.getElementById("draftRows");
        if (!drafts || !drafts.length) {
            tbody.innerHTML = `
              <tr>
                <td colspan="4" style="text-align:center; color:var(--text-secondary); 
                                       padding:40px;">
                  No drafts detected.
                </td>
              </tr>`;
            return;
        }
        tbody.innerHTML = drafts.map(d => `
          <tr>
            <td>
              <div style="font-weight:700; color:var(--accent-cyber); margin-bottom:4px;">
                ${d.title}
              </div>
              <div class="content-preview">${d.body}</div>
            </td>
            <td>
              <a href="${d.source_url}" target="_blank" class="tag" 
                 style="text-decoration:none;">VIEW ORIGIN</a>
            </td>
            <td style="font-size:0.8rem; color:var(--text-secondary);">
              ${new Date(d.created_at).toLocaleString()}
            </td>
            <td>
              <div style="display:flex; gap:8px;">
                <button class="btn btn-primary" 
                        onclick="handlePost(${d.id}, 'approve')">Publish</button>
                <button class="btn btn-secondary" 
                        onclick="handlePost(${d.id}, 'reject')">Discard</button>
              </div>
            </td>
          </tr>
        `).join("");
      }

      function renderMemory(recent) {
        const overviewTable = document.getElementById("memoryRowsOverview");
        if (!recent || !recent.length) {
          overviewTable.innerHTML = '<tr><td colspan="4" class="muted">No historical data.</td></tr>';
          return;
        }
        const rows = recent.map((item) => `
          <tr>
            <td><span class="tag">${item.text_hash.slice(0,12)}</span></td>
            <td style="font-weight:700; color:${
              item.action === 'remove' ? 'var(--accent-pulse)' : 'var(--accent-neon)'
            }">
              ${item.action.toUpperCase()}
            </td>
            <td style="font-size:0.85rem;">${item.reason}</td>
            <td style="font-size:0.8rem; color:var(--text-secondary);">
              ${new Date(item.created_at).toLocaleString()}
            </td>
          </tr>
        `).join("");
        overviewTable.innerHTML = rows;
      }

      async function resolveReview(caseId) {
        const status = document.getElementById(`status-${caseId}`).value;
        await fetch(`/reviews/${caseId}/resolve`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status }),
        });
        await refreshDashboard();
      }

      async function handlePost(postId, action) {
        await fetch(`/posts/${postId}/action`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action }),
        });
        await refreshDashboard();
      }

      async function refreshDashboard() {
        try {
          const [metrics, reviews, memory, drafts, config] = await Promise.all([
            fetchJson("/metrics"),
            fetchJson("/reviews"),
            fetchJson("/memory"),
            fetchJson("/posts/pending"),
            fetchJson("/config"),
          ]);
          
          document.getElementById("currentModel").textContent = config.ai_model.toUpperCase();
          document.getElementById("commentsProcessed").textContent = 
            metrics.comments_processed ?? 0;
          document.getElementById("actionsTaken").textContent = metrics.actions_taken ?? 0;
          document.getElementById("queuedReviews").textContent = metrics.queued_reviews ?? 0;
          document.getElementById("postsProcessed").textContent = metrics.posts_processed ?? 0;
          
          renderReviews(reviews.pending);
          renderMemory(memory.recent);
          renderDrafts(drafts.drafts);
        } catch (error) {
          console.error(error);
        }
      }

      refreshDashboard();
      setInterval(refreshDashboard, 15000);
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


@app.get("/config")
def get_config() -> dict[str, Any]:
    return {"ai_model": os.getenv("AI_MODEL", "openai/gpt-4o-mini")}


@app.get("/metrics")
def metrics(db: Session = Depends(get_db)) -> dict[str, int]:
    today = date.today()
    history = db.query(DailyMetric).filter(DailyMetric.metric_date == today).all()
    totals = {
        "posts_processed": 0,
        "comments_processed": 0,
        "queued_reviews": 0,
        "actions_taken": 0,
    }
    for h in history:
        if h.metric_name in totals:
            totals[h.metric_name] += h.count
    session_snapshot = metrics_store.snapshot()
    for k, v in session_snapshot.items():
        if k in totals:
            totals[k] += v
    return totals


@app.get("/analytics/growth")
def growth_analytics(db: Session = Depends(get_db)) -> dict[str, Any]:
    end_date = date.today()
    start_date = end_date - timedelta(days=7)
    records = db.query(DailyMetric).filter(DailyMetric.metric_date >= start_date).all()
    dates = sorted(list({r.metric_date.isoformat() for r in records}))
    metrics_data = {}
    for r in records:
        d_str = r.metric_date.isoformat()
        if r.metric_name not in metrics_data:
            metrics_data[r.metric_name] = {}
        metrics_data[r.metric_name][d_str] = r.count
    return {"dates": dates, "metrics": metrics_data}


@app.get("/posts/pending")
def list_pending_posts(db: Session = Depends(get_db)) -> dict[str, List[dict]]:
    posts = db.query(PendingPost).filter(PendingPost.status == "pending").all()
    return {
        "drafts": [
            {
                "id": p.id,
                "title": p.title,
                "body": p.body,
                "source_url": p.source_url,
                "created_at": p.created_at.isoformat(),
            }
            for p in posts
        ]
    }


@app.post("/posts/{post_id}/action")
def take_post_action(
    post_id: int, payload: PostActionRequest, db: Session = Depends(get_db)
) -> dict:
    post = db.query(PendingPost).filter(PendingPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    if payload.action == "approve":
        post.status = "approved"
        metrics_store.increment("posts_processed")
    else:
        post.status = "rejected"

    db.commit()
    return {"ok": True}


@app.get("/reviews")
def reviews(db: Session = Depends(get_db)) -> dict[str, list[dict[str, Any]]]:
    return {"pending": list_queue(db, status="pending")}


@app.post("/reviews/{case_id}/resolve")
def resolve_review(
    case_id: str, payload: ReviewResolutionRequest, db: Session = Depends(get_db)
) -> dict[str, Any]:
    updated = resolve_case(db, case_id, payload.status, payload.reviewer_note)
    if not updated:
        raise HTTPException(status_code=400, detail="Unable to resolve review case.")
    return {"ok": True, "pending": list_queue(db, status="pending")}


@app.get("/memory")
def memory(db: Session = Depends(get_db)) -> dict[str, list[dict[str, Any]]]:
    return {"recent": recent_cases(db)}
