# PrepSathi — launch checklist

The exact flip-switch steps for going live, in order. Everything here is
free-tier and needs no card. Two steps are Samir's own taps and cannot be
done by an agent: provisioning Neon Postgres (step 2) and applying the
Render blueprint from his Render account (step 1).

**Status at writing (16 Nov 2026): NOT LIVE.** No live URL exists yet —
see "Deploy assessment — 16 Nov 2026" below. The flip-switch date is
**1 Dec 2026**, when Render's free instance hours reset.

Live URLs once deployed (from `render.yaml`):

| Service | URL |
|---|---|
| Frontend (static) | https://prepsathi.onrender.com |
| Backend API (web service) | https://prepsathi-api.onrender.com |

## Pre-launch checks

Run these before touching Render. Every one must pass.

- [ ] **Tests green.** Backend: `cd backend && ../.venv/bin/python -m pytest tests/ -q`
      (172 passed at v0.3.0 — re-run on launch day, do not trust the old
      number). Frontend: `cd frontend && npm run typecheck && npm run build`.
- [ ] **No Cambridge content.** No copied test papers, passages, questions,
      answer keys or audio anywhere in `backend/` or `frontend/`, and no
      Cambridge material in the resources hub (links out only — never
      mirrored or re-hosted files). The product name must not use "IELTS"
      or "Cambridge" as its brand.
- [ ] **Band labels present.** Every band shown anywhere — Listening,
      Reading, Writing ranges, Speaking ranges, mock overall band —
      carries the label **"practice estimate, not an official score"**,
      in the API response and in the UI. Writing/Speaking give estimated
      ranges, never a precise band, and never promise a band or an outcome.
- [ ] **Privacy note live.** A short note on the site stating what data is
      kept (account email, attempts, vocabulary) and what is not
      (Speaking recordings never leave the device — IndexedDB only).
      Verify it renders on the live frontend before announcing the launch.
- [ ] **Feedback loop live.** Learners can reach Samir with a bug report
      or a content correction (whatever channel Phase 4 ships — form,
      email link, or GitHub issue link). Verify a test message actually
      arrives before announcing the launch.
- [ ] **Listening audio note honest.** Listening tests still ship with
      transcripts and an `audio_note` saying audio is coming — no fake
      or synthesised-placeholder audio files anywhere.
- [ ] **Resources hub links still live.** Re-check the five links in
      `docs/phase3-spec.md` §5 on launch day; a dead official link is
      worse than no link.
- [ ] **Local smoke test passes.** Signup → practice test → dashboard →
      mock start → submit → overall band, against the local backend,
      exactly as the v0.3.0 coordinator smoke test did.

## Step 1 — Apply the Render blueprint

Samir's tap, in his Render dashboard (no card needed for the free tier).

1. In Render: **New → Blueprint**, connect the
   `Samir-Khadka/prep-sathi` repo, select `render.yaml`.
2. Render creates two services from the blueprint:
   - **Static site `prepsathi`** — build:
     `cd frontend && npm ci --ignore-scripts && npm run build`,
     publish dir `frontend/dist`, env `VITE_API_URL=https://prepsathi-api.onrender.com`.
   - **Web service `prepsathi-api`** (Python, free plan) — build:
     `pip install -r backend/requirements.txt`, start:
     `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
3. The first deploy will fail its health check until step 2 is done
   (no database yet) — that is expected. Do not delete the service;
   finish step 2 and redeploy with **Manual Deploy → Deploy latest commit**.

## Step 2 — Provision Neon Postgres and set DATABASE_URL

Samir's tap — Neon provisioning needs his own account; no agent can or
should do this for him.

1. Sign in to Neon (free tier, no card) and create a project, e.g.
   `prepsathi`, region closest to the Render service (Oregon if offered).
2. Create a database, e.g. `prepsathi`, and copy the connection string.
   It looks like:
   `postgresql://<user>:<password>@<host>/<database>?sslmode=require`
3. In Render, open the `prepsathi-api` service → **Environment** → set
   `DATABASE_URL` to that connection string. Never commit it to the repo.
4. Redeploy the backend. On first boot the app creates its own tables
   (`init_db()` on startup); there is no migration step.
5. Note: Neon's free tier is the durable-database choice here. Render's
   own free Postgres expires after ~30 days, which is why the blueprint
   leaves `DATABASE_URL` unset (`sync: false`) instead of provisioning
   one.

## Step 3 — Set the backend env vars

In Render, `prepsathi-api` → **Environment**. The code reads exactly
these (see `backend/app/config.py`):

| Variable | Value |
|---|---|
| `DATABASE_URL` | Neon Postgres URL from step 2 |
| `PREPSATHI_JWT_SECRET` | A long random string. The blueprint sets `generateValue: true`, so Render generates one on first apply — verify it is set and never use the `dev-only-placeholder-change-me-in-production` default. Rotating it later logs every learner out (JWTs are 7-day). |
| `CORS_ORIGINS` | `https://prepsathi.onrender.com` (already the blueprint default; add the custom domain here too if one is ever pointed at the frontend) |
| `JWT_EXPIRE_DAYS` | `7` (default; only set explicitly if the session length changes) |
| `ADMIN_EMAILS` | Comma-separated admin emails for the feedback admin view (`GET /api/feedback/admin`, added in v0.4.0). The router reads it from the environment at request time; empty means no admin access (403 for everyone). Set it to Samir's email at deploy time. |

Frontend env (set at build time by the blueprint, not in the dashboard):

| Variable | Value |
|---|---|
| `VITE_API_URL` | `https://prepsathi-api.onrender.com` |

After changing any env var, redeploy the affected service — Render does
not pick up env changes on a running instance.

## Step 4 — Verify end-to-end on the live URL

Do this in a real browser, signed out, on the live URLs — not against
localhost.

1. Open https://prepsathi.onrender.com — the landing page loads.
2. **Signup** a fresh test account (email + password). Confirm the
   dashboard loads and the JWT persists across a refresh.
3. **Practice:** start a timed Listening test, answer a few questions,
   submit — score and band appear with the "practice estimate, not an
   official score" label.
4. **Dashboard:** the attempt shows up, section trend and target band
   update.
5. **Mock:** start a mock (Academic track), submit Listening and
   Reading, submit Writing with model-answer-length text, complete
   Speaking with a fluency range — the overall band appears and the
   mock status is `complete`.
6. **Cold start check:** wait 20 minutes with no traffic, then load a
   page that calls the API. The backend sleeps after 15 minutes idle
   and takes ~30–60 seconds to wake. The frontend must show a loading
   state during the wake-up, not an error page. If it errors, fix the
   loading state before announcing the launch — this is the normal
   free-tier behaviour, not a bug.
7. Check `https://prepsathi-api.onrender.com/api/health` returns
   `{"status": "ok", "app": "prepsathi", "version": "0.3.0"}` (or the
   then-current version).

Only after all seven pass is the launch real. Announce it then — not
before.

## Step 5 — Monitoring

**The Render lesson, stated plainly:** free instance hours are finite
and shared — **750 hours/month per workspace, across every free web
service in it**. In November 2026 that quota was exhausted and Render
suspended ALL free web services in the workspace until 1 Dec. The most
likely cause is the 5-minute UptimeRobot pings that kept every service
awake 24/7. Do not repeat it.

- **Do NOT set up aggressive uptime pings.** No 5-minute checks, no
  keep-alive cron. A ping every 5 minutes keeps the service awake
  around the clock and burns the whole month's quota on one service.
  If any monitoring is wanted, it is at most one check a day — and even
  that is optional.
- **The backend is allowed to sleep.** Free web services spin down
  after 15 minutes without traffic and wake in ~30–60 seconds. That is
  the deal for $0. The frontend is a static site: it never sleeps and
  must keep working while the backend wakes (see the cold-start check
  in step 4).
- **Watch the quota, not the uptime.** In the Render dashboard, check
  remaining free instance hours once a week. If the workspace is
  trending to run out before month-end, the fix is fewer awake hours
  (let services sleep), not more monitoring. Paid escape hatch, if Samir
  ever wants it: Render Starter at $7/month, always on, no hour cap.
- **Watch the database too.** Neon free tier has its own limits
  (storage / compute hours); check the Neon dashboard monthly. The
  backend's SQLite fallback is local-dev only and must never be used in
  production.
- **When something breaks:** check Render's service status and the
  workspace's remaining hours first. A 503 "Service Suspended" page
  means the quota is gone, not that the code is broken — restarting the
  service does not fix it.

## Deploy assessment — 16 Nov 2026

**Conclusion: no real live deployment is possible today.**

Verified 16 Nov 2026 (~20:41 NPT) by curl:

```
$ curl https://vedic-astro-ggel.onrender.com
HTTP 503 — "Service Suspended"
```

Render's free web services in Samir's workspace are still suspended
until 1 Dec 2026 (750 free instance hours exhausted). The suspension is
workspace-wide, so a new `prepsathi-api` web service would be suspended
on creation exactly like the existing ones. The static frontend is
unaffected by the suspension — static sites do not consume instance
hours — but a static frontend alone is **not** a live deployment:
end-to-end needs the backend (auth, timed tests, dashboard, mocks all
call the API), and the frontend against a dead API is a demo shell.

Could another free host carry the backend today instead? No — not
without Samir's own account, and not honestly for free:

- **Render (the plan's host):** free tier needs no card, but it needs
  Samir's Render account connected to the repo, and the workspace
  quota is exhausted until 1 Dec anyway.
- **Railway:** trial is a one-time $5 credit for 30 days, no card, then
  a Free plan of $1 of credit a month — about 6 days of runtime for one
  small service, not a month. Needs Samir's Railway account.
- **Fly.io:** no free tier for new accounts at all; only a trial of
  2 machine-hours or 7 days, and a card is required to keep anything
  running after it. Needs Samir's account and, after the trial, a card.
- **Neon Postgres:** free tier, no card — but it is Samir's account to
  create, and a database alone is not a deployment.

No account was created, no signup was attempted, and no live URL is
claimed here, because none of those steps can be done without Samir's
accounts and none of them would produce a working backend today
anyway. The honest path is the 1 Dec flip-switch: steps 1–5 above, in
order, on or after 1 Dec 2026 when the Render hours reset. Until then
the product runs locally (`README.md` — backend on :8000, frontend
on :5173) and the pre-launch checks above are the work that can be
done now.

Sources for the free-tier claims above: Render's own pricing/free-tier
docs via render.com (no card for the free tier; 750 hrs/month shared;
spin-down after 15 min idle) and third-party free-tier surveys checked
Oct–Nov 2026 (Railway $5 trial then $1/month; Fly.io trial-only for new
accounts). Re-verify against the providers' own pages on launch day —
free-tier terms move.
