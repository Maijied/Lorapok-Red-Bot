# Business Model: Lorapok Red Bot

---

## 1. Executive Summary

Lorapok Red Bot is a full-spectrum Reddit automation platform sold as a SaaS product to
subreddit moderators, community managers, and Reddit marketing agencies. It automates every
controllable surface of the Reddit API — moderation, user management, flair, wiki, modmail,
widgets, rules, analytics, and content scheduling — wrapped in a professional dashboard built
with the Lorapok Design Language.

The product is free to self-host (open-source core on GitHub) and commercially available as
a hosted service with five tiers: Free, Starter ($19/mo), Pro ($49/mo), Agency ($149/mo), and
Enterprise (custom). Revenue comes primarily from monthly subscriptions, with secondary streams
from AI token pass-through, a template marketplace, and white-label licensing.

The core insight: Reddit has over 100,000 active subreddits. Most are moderated by volunteers
with no tooling beyond Reddit's native interface. A professional automation layer that looks
and feels like a real product is a clear gap in the market.

---

## 2. Market Opportunity

### The Reddit Moderation Pain Point

- Reddit has 100,000+ active subreddits and 73 million daily active users (2024).
- The top 1,000 subreddits each have 100k–50M+ subscribers, moderated by teams of 2–20 volunteers.
- Moderators report spending 5–20 hours per week on repetitive tasks: removing spam, answering
  the same modmail questions, assigning flair, updating wiki pages.
- Reddit's native moderation tools have not meaningfully improved in years.
- No well-known SaaS product exists specifically for Reddit community automation.

### Addressable Market

| Segment | Count | Conversion Assumption | ARR Potential |
|---|---|---|---|
| Subreddits with 10k–100k subscribers | ~15,000 | 1% at Starter | $342,000 |
| Subreddits with 100k–1M subscribers | ~3,000 | 2% at Pro | $352,800 |
| Subreddits with 1M+ subscribers | ~500 | 3% at Agency | $322,200 |
| Reddit marketing agencies | ~200 | 5% at Agency | $178,200 |

Conservative total addressable ARR at low conversion: ~$1.2M. At 5% conversion across all
segments: ~$6M ARR. Reddit's user base is growing and moderation tooling demand grows with it.

### Why Now

- Reddit went public in 2024, increasing institutional interest in the platform.
- AI APIs (OpenAI, Anthropic) are now cheap enough to make per-comment classification
  economically viable at scale.
- The open-source bot ecosystem (PRAW, AutoModerator) is mature but lacks a polished SaaS
  layer on top.

---

## 3. Product Tiers and Feature Matrix

### Tier Definitions

**Free / Community — $0/month**: 1 subreddit, basic moderation, 100 AI calls/day, public
dashboard, Discord + GitHub integration, community support.

**Starter — $19/month**: 3 subreddits, 1,000 AI calls/day, modmail triage, flair automation,
basic analytics, review queue dashboard, email support (48h SLA).

**Pro — $49/month**: 10 subreddits, unlimited AI, advanced analytics, cohort analysis,
engagement predictor, sentiment analysis, content calendar, cross-sub spam detection, wiki
manager, widget manager, Slack + Telegram integration, ban appeal workflow, contributor
management, priority support (24h SLA).

**Agency — $149/month**: Unlimited subreddits, white-label dashboard, API access, custom
webhooks, policy sync, multi-sub dashboard, mod notes, rules engine v2, health score,
dedicated support (4h SLA).

**Enterprise — Custom**: On-premise, custom AI models, SSO (SAML/OIDC), audit logs,
compliance reports, SLA guarantee, dedicated account manager.

### Feature Matrix

| Feature | Free | Starter | Pro | Agency | Enterprise |
|---|:---:|:---:|:---:|:---:|:---:|
| Subreddits | 1 | 3 | 10 | Unlimited | Unlimited |
| AI calls/day | 100 | 1,000 | Unlimited | Unlimited | Unlimited |
| Basic moderation | Yes | Yes | Yes | Yes | Yes |
| Comment stream | Yes | Yes | Yes | Yes | Yes |
| Dashboard | Yes | Yes | Yes | Yes | Yes |
| Discord integration | Yes | Yes | Yes | Yes | Yes |
| GitHub integration | Yes | Yes | Yes | Yes | Yes |
| Modmail triage | — | Yes | Yes | Yes | Yes |
| Flair automation | — | Yes | Yes | Yes | Yes |
| Basic analytics | — | Yes | Yes | Yes | Yes |
| Advanced analytics | — | — | Yes | Yes | Yes |
| Engagement predictor | — | — | Yes | Yes | Yes |
| Sentiment analysis | — | — | Yes | Yes | Yes |
| Content calendar | — | — | Yes | Yes | Yes |
| Cross-sub spam detection | — | — | Yes | Yes | Yes |
| Wiki manager | — | — | Yes | Yes | Yes |
| Widget manager | — | — | Yes | Yes | Yes |
| Slack integration | — | — | Yes | Yes | Yes |
| Telegram integration | — | — | Yes | Yes | Yes |
| Ban appeal workflow | — | — | Yes | Yes | Yes |
| Contributor management | — | — | Yes | Yes | Yes |
| White-label | — | — | — | Yes | Yes |
| API access | — | — | — | Yes | Yes |
| Custom webhooks | — | — | — | Yes | Yes |
| Policy sync | — | — | — | Yes | Yes |
| Multi-sub dashboard | — | — | — | Yes | Yes |
| Mod notes system | — | — | — | Yes | Yes |
| Rules engine v2 | — | — | — | Yes | Yes |
| Health score | — | — | — | Yes | Yes |
| SSO | — | — | — | — | Yes |
| On-premise | — | — | — | — | Yes |
| Audit logs | — | — | — | — | Yes |
| Custom AI models | — | — | — | — | Yes |

---

## 4. Pricing Strategy and Rationale

**Free tier** drives organic adoption. Reddit moderators are a word-of-mouth community — a
useful free tier spreads through mod team Discord servers and subreddit meta posts. It also
builds GitHub stars and trust via the open-source codebase.

**Starter at $19/mo** sits below the psychological $20 threshold. It targets individual
moderators of mid-size subreddits (10k–500k subscribers) spending 5+ hours/week on modmail
and flair. The ROI is obvious after saving one hour of their time.

**Pro at $49/mo** targets power moderators and small mod teams managing multiple subreddits.
Unlimited AI calls and advanced analytics justify the jump from Starter. The content calendar
and engagement predictor are unique features not available anywhere else for Reddit.

**Agency at $149/mo** targets Reddit marketing agencies and large community operators. The
white-label dashboard lets agencies resell under their own brand. At $149/mo for unlimited
subreddits, the per-subreddit cost drops below $15 for agencies managing 10+.

**Enterprise** starts at $500/mo. Targets large media companies, gaming studios, and tech
companies with official subreddits needing on-premise deployment, SSO, and compliance reports.

### Annual Discount

2 months free on annual plans (16.7% discount):
- Starter annual: $190/yr (vs. $228/yr monthly)
- Pro annual: $490/yr (vs. $588/yr monthly)
- Agency annual: $1,490/yr (vs. $1,788/yr monthly)

### AI Token Pass-Through

For unlimited AI tiers (Pro+), AI API costs are passed through at cost + 20% markup,
transparent in the billing dashboard. At current OpenAI pricing (~$0.15/1M tokens for
gpt-4o-mini), a subreddit processing 10,000 comments/day costs ~$0.45/day in AI costs.

---

## 5. Revenue Projections

### Conservative Scenario (Year 1)

| Month | Free | Starter | Pro | Agency | MRR |
|---|---|---|---|---|---|
| 1 | 50 | 5 | 1 | 0 | $144 |
| 3 | 200 | 20 | 5 | 1 | $678 |
| 6 | 500 | 60 | 18 | 4 | $2,238 |
| 9 | 900 | 110 | 38 | 9 | $4,451 |
| 12 | 1,500 | 170 | 65 | 18 | $7,352 |

**Year 1 ARR (conservative)**: ~$88,000

### Realistic Scenario (Year 1)

| Month | Free | Starter | Pro | Agency | MRR |
|---|---|---|---|---|---|
| 1 | 100 | 12 | 3 | 0 | $375 |
| 3 | 500 | 55 | 15 | 3 | $1,732 |
| 6 | 1,500 | 150 | 50 | 12 | $6,238 |
| 9 | 3,000 | 280 | 100 | 25 | $12,082 |
| 12 | 5,000 | 420 | 170 | 45 | $19,505 |

**Year 1 ARR (realistic)**: ~$234,000

### Optimistic Scenario (Year 1 — viral post or press coverage)

| Month | Free | Starter | Pro | Agency | MRR |
|---|---|---|---|---|---|
| 3 | 2,000 | 150 | 45 | 10 | $5,235 |
| 6 | 8,000 | 450 | 150 | 35 | $18,435 |
| 12 | 20,000 | 1,200 | 450 | 100 | $52,350 |

**Year 1 ARR (optimistic)**: ~$628,000

### Year 2 Targets (Realistic Path)

10,000 free users, 800 Starter, 350 Pro, 100 Agency, 5 Enterprise.
MRR: ~$42,000 (~$504,000 ARR). Enterprise contracts add $30,000–$60,000 ARR.
**Total Year 2 ARR target**: ~$550,000.

---

## 6. Customer Acquisition Strategy

### Channel 1: Reddit Communities (Primary, Zero Cost)

Reddit moderators live on Reddit. The best acquisition channel is Reddit itself.

- Post to r/redditdev, r/modhelp, r/modnews, r/automation.
- Write a "Show HN"-style post on r/programming and r/Python.
- Offer free Pro tier to moderators of large subreddits in exchange for testimonials.
- Participate in r/modhelp threads where moderators ask for automation help.
- Create r/LorapokRedBot as the official community subreddit (dogfooding the product).

**Expected result**: 500–2,000 free signups in the first month from a well-received post.

### Channel 2: Developer Communities

- Post to Hacker News (Show HN), Product Hunt, and Dev.to.
- GitHub repository with a compelling README, demo GIF, and one-click Railway deploy button.
- Technical blog posts: "How we built a Reddit bot with PRAW and LiteLLM", "Building a
  multi-tenant SaaS on FastAPI".
- Sponsor Python and Reddit API newsletters.

**Expected result**: 200–500 GitHub stars in month 1; 50–150 signups.

### Channel 3: SEO Content

Target long-tail keywords: "reddit moderation bot", "automate reddit moderation",
"reddit bot python", "reddit modmail automation", "reddit flair automation".
Write 2–4 articles per month. At 6 months: 500–2,000 organic monthly visitors.

### Channel 4: Reddit Ads (Month 6+)

Target moderators of subreddits with 10k+ subscribers via Reddit's subreddit-membership
targeting. Budget: $500–$2,000/month. Expected CAC: $30–$80 for Starter.

### Channel 5: Agency Partnerships

Reach out to Reddit marketing agencies managing brand subreddits. Offer white-label Agency
tier with revenue share for referrals. Target: 5–10 agency partners in Year 1.

---

## 7. Competitive Analysis

### Direct Competitors

| Product | Focus | Weakness vs. Lorapok |
|---|---|---|
| AutoModerator (Reddit native) | Rule-based moderation | No AI, no dashboard, no analytics, no SaaS |
| Modmail.io | Modmail management only | Single feature, no moderation, no analytics |
| Toolbox (browser extension) | Mod workflow helpers | Browser-only, no automation, no AI |
| PRAW scripts (DIY) | Custom bots | Requires coding, no UI, no SaaS |

### Indirect Competitors

| Product | Focus | Weakness vs. Lorapok |
|---|---|---|
| Discourse | Forum software | Not Reddit-specific |
| Commsor | Community analytics | No moderation, no Reddit API automation |
| Orbit | Community CRM | No moderation, no Reddit-specific features |

### Competitive Moat

1. **Full Reddit API coverage** — no competitor covers every PRAW endpoint in a single product.
2. **Lorapok Design Language** — the biological UI and glassmorphism aesthetic create strong
   brand identity. Moderators recognise the dashboard immediately.
3. **Data flywheel** — the memory system and reputation scores improve per-tenant over time.
   The longer a customer uses the product, the better it gets for their community.
4. **Multi-subreddit network effects** — cross-subreddit spam detection only works when
   multiple subreddits are managed by the same tenant, creating a switching cost.
5. **Open-source trust** — moderators can audit the code before granting bot permissions.
   Significant trust advantage over closed competitors.
6. **Genuinely useful free tier** — drives word-of-mouth and GitHub stars.

---

## 8. Monetisation Roadmap

### Phase 0: Foundation (Weeks 1–4)

Build the MVP that justifies a Starter subscription:
1. Working comment moderation with AI classifier.
2. Modmail triage with auto-reply.
3. Flair automation (post flair by content).
4. Dashboard with review queue and basic metrics.
5. Stripe integration (Starter tier only).
6. One-click Railway deploy button in README.

**Revenue target**: $0 (free users only, building trust).

### Phase 1: First Revenue (Months 1–3)

1. Post to r/redditdev, r/modhelp, Hacker News, Product Hunt.
2. Offer free Pro tier to 10 large subreddit moderators for testimonials.
3. Enable Starter and Pro tiers in Stripe.
4. Add GitHub integration (trending posts) — unique value for developer subreddits.
5. Add Discord integration — every mod team uses Discord.

**Revenue target**: $500–$2,000 MRR by end of Month 3.

### Phase 2: Growth Features (Months 3–6)

1. Advanced analytics (cohort analysis, engagement predictor, health score).
2. Content calendar with optimal posting times.
3. Cross-subreddit spam detection.
4. Slack integration.
5. Wiki manager and widget manager.
6. Agency tier with white-label dashboard.

**Revenue target**: $5,000–$15,000 MRR by end of Month 6.

### Phase 3: Enterprise and Scale (Months 6–12)

1. Enterprise tier with SSO and on-premise deployment.
2. Zapier/Make integration (no-code automation triggers).
3. Template marketplace (community-built rule templates, flair packs).
4. Paid acquisition via Reddit ads.
5. Agency partnership programme.

**Revenue target**: $15,000–$50,000 MRR by end of Month 12.

### What to Build First for Fastest Revenue

Priority order based on willingness-to-pay signals:
1. **Modmail triage** — moderators hate answering the same questions. Immediate time savings.
2. **Flair automation** — every subreddit with flair needs this. Easy to demo.
3. **Stripe billing** — needed before any revenue.
4. **Advanced analytics** — justifies Pro upgrade. Moderators want data.
5. **White-label dashboard** — unlocks Agency tier. High-value, low-effort feature.
6. **Webhook system** — unlocks Agency tier. Agencies need custom integrations.

---

## 9. Unit Economics

### Customer Acquisition Cost (CAC)

| Channel | Estimated CAC |
|---|---|
| Organic Reddit / GitHub | $0 |
| SEO content | $10–$30 (content creation cost amortised) |
| Reddit ads | $30–$80 |
| Agency partnerships | $50–$150 (referral fee) |

**Blended CAC target**: < $40 for Starter, < $100 for Pro.

### Lifetime Value (LTV)

| Tier | Monthly Price | Avg. Lifetime (months) | LTV |
|---|---|---|---|
| Starter | $19 | 18 | $342 |
| Pro | $49 | 24 | $1,176 |
| Agency | $149 | 36 | $5,364 |
| Enterprise | $500+ | 48+ | $24,000+ |

**LTV:CAC ratios**: Starter 8.6x, Pro 11.8x, Agency 35.8x. All well above the 3x minimum.

### Churn Assumptions

| Tier | Monthly Churn | Rationale |
|---|---|---|
| Starter | 5% | Price-sensitive; some churn after initial curiosity |
| Pro | 3% | More invested; using advanced features |
| Agency | 2% | High switching cost; white-label dependency |
| Enterprise | 1% | Contract-based; high switching cost |

### Gross Margin

| Cost Component | Monthly Estimate (at $10k MRR) |
|---|---|
| AI API costs (LiteLLM pass-through) | $200–$500 |
| PostgreSQL + Redis (Railway/Render) | $50–$100 |
| Stripe fees (2.9% + $0.30) | $290–$350 |
| Support (async, founder-led) | $0 (Phase 1) |
| **Total COGS** | ~$640–$950 |
| **Gross Margin** | ~90–94% |

### Break-Even Analysis

Fixed monthly costs: Railway/Render hosting ($50–$100), domain + email ($15).
**Total fixed costs**: ~$65–$115/mo.
**Break-even MRR**: ~$115 (approximately 6 Starter customers). Achievable in Week 1 of launch.

---

## 10. Technical Implementation of Billing

### Architecture Overview

Billing lives in `app/billing/` with three sub-modules: `stripe_client.py` (Stripe API calls),
`features.py` (feature flag enforcement), and `tenant.py` (tenant lifecycle management).

### Stripe Integration Flow

```
Customer signs up
    POST /billing/create-customer
    stripe.Customer.create(email, name)
    TenantConfig.stripe_customer_id = customer.id

Customer selects a tier
    POST /billing/subscribe {price_id}
    stripe.Subscription.create(customer_id, price_id)
    TenantConfig.tier = "starter" | "pro" | "agency"

Stripe webhook events  POST /billing/stripe-webhook
    customer.subscription.updated  update TenantConfig.tier
    customer.subscription.deleted  downgrade to "free"
    invoice.payment_failed         send alert, 7-day grace period
    invoice.payment_succeeded      confirm tier, reset AI quota

Customer self-serves
    POST /billing/portal
    stripe.billing_portal.Session.create(customer_id, return_url)
    Redirect to Stripe-hosted portal (upgrade, downgrade, cancel, update card)
```

### Stripe Price IDs (env vars)

```
STRIPE_PRICE_STARTER_MONTHLY=price_...
STRIPE_PRICE_PRO_MONTHLY=price_...
STRIPE_PRICE_AGENCY_MONTHLY=price_...
STRIPE_PRICE_STARTER_ANNUAL=price_...
STRIPE_PRICE_PRO_ANNUAL=price_...
STRIPE_PRICE_AGENCY_ANNUAL=price_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### Feature Flag Enforcement (Two Layers)

**Layer 1 — API middleware** (`app/billing/middleware.py`):
```python
@app.middleware("http")
async def feature_gate_middleware(request: Request, call_next):
    # Extract tenant_id from JWT or API key header
    # Check has_feature(db, tenant_id, required_feature_for_endpoint)
    # Return 403 with upgrade prompt if not entitled
    pass
```

**Layer 2 — Domain layer** (before any Reddit API call):
```python
if not has_feature(db, tenant_id, "flair_automation"):
    logger.info(f"Tenant {tenant_id} not entitled to flair_automation, skipping")
    return None
```

Both layers are required. The API layer protects the dashboard. The domain layer protects
background workers running outside the HTTP request cycle.

### Tenant Isolation

Every DB table with tenant-specific data has a `tenant_id` column. All queries include a
`WHERE tenant_id = ?` filter enforced by convention in the domain layer and verified in
integration tests. `TenantConfig.managed_subreddits` is the authoritative list of subreddits
a tenant can act on — the worker checks this before processing any subreddit event.

### AI Quota Tracking

```python
# Hot path — Redis counter (avoids per-comment DB write)
if not has_feature(db, tenant_id, "ai_call"):
    return fallback_to_rules_only()
redis.incr(f"ai_calls:{tenant_id}:{today_utc}")

# APScheduler job at midnight UTC resets counters
redis.delete(f"ai_calls:{tenant_id}:{yesterday_utc}")
db.execute("UPDATE tenant_configs SET ai_calls_today = 0")
```

### Stripe Webhook Verification

```python
import stripe

def handle_stripe_webhook(payload: bytes, sig_header: str) -> None:
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")

    if event["type"] == "customer.subscription.updated":
        update_tenant_tier(db, event["data"]["object"])
    elif event["type"] == "customer.subscription.deleted":
        downgrade_tenant_to_free(db, event["data"]["object"])
    elif event["type"] == "invoice.payment_failed":
        send_payment_failed_alert(event["data"]["object"])
```

### Outbound Webhook Security

All outbound webhooks to customer endpoints are signed with HMAC-SHA256:

```python
import hmac, hashlib, json

def sign_payload(payload: dict, secret: str) -> str:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()

# Header on every outbound webhook request:
# X-Lorapok-Signature: sha256=<hex_digest>
```

### White-Label Implementation

Agency and Enterprise tenants configure:
- `TenantConfig.white_label_name` — replaces "Lorapok Red Bot" in the dashboard title.
- `TenantConfig.white_label_logo_url` — replaces the Lorapok logo.
- Custom domain via CNAME to the hosted dashboard (e.g., `bot.theiragency.com`).

The dashboard HTML reads these values from the `/config` endpoint at runtime. No rebuild needed.

---

## 11. Lorapok Design Language in the Product

The Lorapok Design Language is a business asset, not just an aesthetic choice. It creates
immediate visual differentiation from every other Reddit tool (plain HTML or generic Bootstrap).

### Design Tokens

```css
:root {
  --bg-deep: #050505;
  --bg-panel: rgba(20, 22, 28, 0.7);
  --accent-neon: #39ff14;       /* primary CTA, active states */
  --accent-cyber: #00f3ff;      /* data highlights, tags */
  --accent-pulse: #ff2f55;      /* alerts, removals */
  --accent-reddit: #FF4500;     /* Reddit brand integration */
  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --border-glass: rgba(255, 255, 255, 0.08);
  --glow-green: 0 0 15px rgba(57, 255, 20, 0.3);
  --glow-reddit: 0 0 15px rgba(255, 69, 0, 0.4);
}
```

### Biological UI Principles

- Panels use `backdrop-filter: blur(12px)` and semi-transparent backgrounds (glassmorphism).
- Animated pulse dots indicate live system status.
- Grid backgrounds with radial gradient masks create depth without distraction.
- Hover states use `transform: translateY(-4px)` for a floating feel.
- All interactive elements have `transition: all 0.2s ease`.

### Application to Business

- The dashboard is the product's primary sales tool. When a moderator sees it for the first
  time, it should feel like a professional product worth paying for.
- The public GitHub Pages marketing site uses the same design language to create a cohesive
  brand experience from first impression to daily use.
- White-label customers inherit the design system — their branded dashboard looks just as
  professional, reinforcing the value of the Agency tier.
- The design quality signals that this is a serious product, not a hobby script. That signal
  is worth real money in a market where the competition is AutoModerator and PRAW scripts.
