# Deploying RailSense-AI on Railway

Step-by-step guide to deploy the full stack (FastAPI + PostgreSQL) on [Railway](https://railway.com/).

## Prerequisites

- GitHub account with the repo pushed
- Railway account (sign up at https://railway.com/)
- API keys for your chosen LLM provider (e.g., DeepSeek)

## Cost

| Plan | Monthly Cost | Notes |
|---|---|---|
| Free Trial | $0 (one-time) | $5 credit, 30-day limit |
| Hobby | $5/month | $5 usage credit included — sufficient for this project |

Two services (Postgres + FastAPI) will consume roughly $2–4/month in resources.

---

## Step 1: Create Railway Project

1. Log in at https://railway.com/
2. Click **"New Project"**
3. Select **"Empty Project"**

## Step 2: Add PostgreSQL

1. In the project canvas, click **"+ New" → "Database" → "PostgreSQL"**
2. Railway provisions a managed PostgreSQL 16 instance automatically
3. It generates connection variables including `DATABASE_URL` — you'll reference this later

## Step 3: Deploy the Application

The FastAPI server serves both the REST API and the HTML dashboard (Jinja2 templates), so only one application service is needed.

1. Click **"+ New" → "GitHub Repo"**
2. Select your `railsense-ai` repository
3. Railway auto-detects the `Dockerfile` and builds the image
4. Go to **Settings → Deploy** and set:
   - **Start Command**: `uvicorn src.api.main:app --host 0.0.0.0 --port 8000`
   - **Health Check Path**: `/health`
5. Go to **Settings → Networking** and click **"Generate Domain"** to create a public URL

## Step 4: Configure Environment Variables

Set these on the application service under the **Variables** tab:

| Variable | Value |
|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (reference variable) |
| `LLM_PROVIDER` | `deepseek` |
| `DEEPSEEK_API_KEY` | *(your key — set in dashboard, never in code)* |
| `LTA_API_KEY` | *(your key, if using live LTA data)* |

The `${{Postgres.DATABASE_URL}}` syntax dynamically references the PostgreSQL service's connection string.

## Step 5: Seed Demo Data

Tables are created automatically on app startup via `Base.metadata.create_all()` — no manual migration needed.

Install the Railway CLI if you haven't already:

```bash
npm install -g @railway/cli
railway login
railway link
```

```bash
railway run python -m scripts.demo_seed
```

## Step 6: Verify

1. Open the public URL generated in Step 3
2. Confirm all four pages load: Live Overview, Sensor Explorer, Alert Feed, Model Comparison
3. Test the AI assessment endpoint (requires a valid LLM API key)

---

## Optional: Config as Code

Instead of configuring via the dashboard, add a `railway.toml` file at the repo root:

```toml
[build]
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
healthcheckPath = "/health"
restartPolicyType = "ON_FAILURE"
```

Then in the Railway dashboard, set the service's **Config File Path** to `railway.toml`.

---

## Troubleshooting

| Issue | Fix |
|---|---|
| Database connection refused | Verify `DATABASE_URL` uses `${{Postgres.DATABASE_URL}}` reference syntax |
| Build fails | Ensure `Dockerfile` and `pyproject.toml` are at repo root |
| Services sleeping | Free trial has resource limits; upgrade to Hobby plan |
| Static files not loading | Verify `src/static/` is included in the Docker image |

---

## References

- [Railway Docs — Dockerfiles](https://docs.railway.com/builds/dockerfiles)
- [Railway Docs — PostgreSQL](https://docs.railway.com/databases/postgresql)
- [Railway Docs — Variables](https://docs.railway.com/variables)
- [Railway Docs — Config as Code](https://docs.railway.com/config-as-code/reference)
- [Railway Docs — Pricing](https://docs.railway.com/reference/pricing/plans)
