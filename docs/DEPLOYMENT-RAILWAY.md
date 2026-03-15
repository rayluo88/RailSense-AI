# Deploying RailSense-AI on Railway

Step-by-step guide to deploy the full stack (FastAPI + Streamlit + PostgreSQL) on [Railway](https://railway.com/).

## Prerequisites

- GitHub account with the repo pushed
- Railway account (sign up at https://railway.com/)
- API keys for your chosen LLM provider (e.g., DeepSeek)

## Cost

| Plan | Monthly Cost | Notes |
|---|---|---|
| Free Trial | $0 (one-time) | $5 credit, 30-day limit |
| Hobby | $5/month | $5 usage credit included — sufficient for this project |

Three services (Postgres + FastAPI + Streamlit) will consume roughly $3–5/month in resources.

---

## Step 1: Create Railway Project

1. Log in at https://railway.com/
2. Click **"New Project"**
3. Select **"Empty Project"**

## Step 2: Add PostgreSQL

1. In the project canvas, click **"+ New" → "Database" → "PostgreSQL"**
2. Railway provisions a managed PostgreSQL 16 instance automatically
3. It generates connection variables including `DATABASE_URL` — you'll reference this later

## Step 3: Deploy the API Service

1. Click **"+ New" → "GitHub Repo"**
2. Select your `railsense-ai` repository
3. Railway auto-detects the `Dockerfile` and builds the image
4. Go to **Settings → Deploy** and set:
   - **Start Command**: `uvicorn src.api.main:app --host 0.0.0.0 --port 8000`
   - **Health Check Path**: `/health`
5. Go to **Settings → Networking** and note the internal hostname (e.g., `api.railway.internal`)

## Step 4: Deploy the Dashboard Service

1. Click **"+ New" → "GitHub Repo"** (same repository)
2. Go to **Settings → Deploy** and set:
   - **Start Command**: `streamlit run src/dashboard/app.py --server.port 8501 --server.address 0.0.0.0`
3. Go to **Settings → Networking** and click **"Generate Domain"** to create a public URL

## Step 5: Configure Environment Variables

Set these on **both** the API and Dashboard services under the **Variables** tab:

| Variable | Value |
|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (reference variable) |
| `LLM_PROVIDER` | `deepseek` |
| `DEEPSEEK_API_KEY` | *(your key — set in dashboard, never in code)* |
| `LTA_API_KEY` | *(your key, if using live LTA data)* |

The `${{Postgres.DATABASE_URL}}` syntax dynamically references the PostgreSQL service's connection string.

Set this **only on the Dashboard service**:

| Variable | Value |
|---|---|
| `API_BASE_URL` | `http://api.railway.internal:8000` |

> **Note:** Railway uses private networking between services via `*.railway.internal` hostnames over Wireguard tunnels. Use `http` (not `https`) for internal service-to-service calls.

## Step 6: Code Changes Required

### 1. Make API base URL configurable in the dashboard

In `src/dashboard/app.py`, change:

```python
API_BASE = "http://localhost:8000"
```

to:

```python
import os
API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")
```

This keeps local development working while allowing Railway to inject the internal URL.

### 2. Database URL

Already configurable via `src/config.py` — the `DATABASE_URL` environment variable is read by Pydantic Settings. No code change needed.

## Step 7: Run Database Migrations

After the API service deploys successfully, run migrations via Railway's CLI or one-off command:

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and link project
railway login
railway link

# Run Alembic migrations against the API service
railway run -s api alembic upgrade head
```

## Step 8: Seed Demo Data

```bash
railway run -s api python scripts/demo_seed.py
```

## Step 9: Verify

1. Open the Dashboard's public URL (generated in Step 4)
2. Confirm all four pages load: Live Overview, Sensor Explorer, Alert Feed, Model Comparison
3. Test the AI assessment endpoint (requires a valid LLM API key)

---

## Optional: Config as Code

Instead of configuring via the dashboard, you can add `railway.toml` files:

**`api.railway.toml`**:
```toml
[build]
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
healthcheckPath = "/health"
restartPolicyType = "ON_FAILURE"
```

**`dashboard.railway.toml`**:
```toml
[build]
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "streamlit run src/dashboard/app.py --server.port 8501 --server.address 0.0.0.0"
restartPolicyType = "ON_FAILURE"
```

Then in the Railway dashboard, set each service's **Config File Path** to the corresponding `.railway.toml` file.

---

## Troubleshooting

| Issue | Fix |
|---|---|
| Dashboard can't reach API | Check `API_BASE_URL` uses `http://api.railway.internal:8000` (not https) |
| Database connection refused | Verify `DATABASE_URL` uses `${{Postgres.DATABASE_URL}}` reference syntax |
| Build fails | Ensure `Dockerfile` and `pyproject.toml` are at repo root |
| Services sleeping | Free trial has resource limits; upgrade to Hobby plan |

---

## References

- [Railway Docs — Dockerfiles](https://docs.railway.com/builds/dockerfiles)
- [Railway Docs — PostgreSQL](https://docs.railway.com/databases/postgresql)
- [Railway Docs — Variables](https://docs.railway.com/variables)
- [Railway Docs — Private Networking](https://docs.railway.com/guides/private-networking)
- [Railway Docs — Config as Code](https://docs.railway.com/config-as-code/reference)
- [Railway Docs — Pricing](https://docs.railway.com/reference/pricing/plans)
