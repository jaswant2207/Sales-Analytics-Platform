# Comprehensive Cloud & Web Deployment Guide

This guide details how to deploy your **ETL Analytics Data Warehouse Dashboard** to external servers and public webpages.

The project is pre-configured with multi-platform deployment configs (`Dockerfile`, `render.yaml`, `railway.json`, `vercel.json`, `netlify.toml`, `Procfile`, and `requirements.txt`).

---

## Quick Comparison of Deployment Methods

| Method | Type | Cost | Best For | URL Example |
| :--- | :--- | :--- | :--- | :--- |
| **Render** *(Recommended)* | Live Python Web Server | **100% Free** | Full backend API + Live ETL features | `https://etl-analytics.onrender.com` |
| **Vercel** | Edge Webpage | **100% Free** | Instant deployment, high speed | `https://etl-analytics.vercel.app` |
| **Netlify** | Edge Webpage | **100% Free** | Drag & drop or GitHub sync | `https://etl-analytics.netlify.app` |
| **GitHub Pages** | Static Webpage | **100% Free** | Native GitHub hosting | `https://username.github.io/project` |
| **Railway / Fly.io** | Container Web Server | Free tier | Production microservices | `https://etl-analytics.up.railway.app` |
| **Docker / VPS** | Self-Hosted Linux Server | Custom | AWS EC2, GCP, DigitalOcean, Ubuntu | `http://your-server-ip:8000` |

---

## OPTION 1: Deploy to Render (Recommended Free Cloud Web Server)

Render provides free hosting for Python web services with automated SSL/HTTPS and live REST API support.

### Step 1: Push your project to GitHub
```bash
git init
git add .
git commit -m "Deploy ETL Analytics Dashboard"
git branch -M main
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/<YOUR_REPO_NAME>.git
git push -u origin main
```

### Step 2: Deploy on Render
1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** -> Select **Web Service** (or select **Blueprint** to use `render.yaml`).
3. Connect your GitHub repository.
4. Set the following configuration:
   - **Name**: `etl-analytics-dashboard`
   - **Language / Runtime**: `Python 3`
   - **Branch**: `main`
   - **Build Command**: `pip install -r requirements.txt && python export_data.py`
   - **Start Command**: `python dashboard.py`
   - **Instance Type**: `Free`
5. Click **Create Web Service**.
6. Render will automatically build the environment, run the data pipeline, and provide a public URL like `https://etl-analytics-dashboard.onrender.com`.

---

## OPTION 2: Deploy to Vercel (Instant Free Edge Webpage)

Vercel provides ultra-fast global CDN hosting for your dashboard webpage.

### Method A: Via Vercel Web Dashboard (1-Click)
1. Go to [Vercel.com](https://vercel.com) and log in with GitHub.
2. Click **Add New...** -> **Project**.
3. Select your GitHub repository.
4. Framework Preset: **Other** (Root Directory: `./`).
5. Click **Deploy**.
6. Your webpage will be live at `https://<your-project>.vercel.app` in under 30 seconds!

### Method B: Via Vercel CLI
```bash
npm install -g vercel
vercel login
vercel deploy --prod
```

---

## OPTION 3: Deploy to Netlify (Free Webpage Hosting)

### Method A: Drag & Drop (Zero Git Required)
1. Log in to [Netlify.com](https://app.netlify.com).
2. Go to the **Sites** tab.
3. Drag and drop this entire project folder into the Netlify upload zone.
4. Netlify will deploy your dashboard webpage instantly!

### Method B: Via Git Sync
1. Click **Add new site** -> **Import an existing project**.
2. Connect your GitHub repo.
3. Build command: *(Leave blank)*.
4. Publish directory: `.` (or root).
5. Click **Deploy Site**.

---

## OPTION 4: Deploy to GitHub Pages (100% Free Public Webpage)

1. Push your code to your GitHub repository.
2. Open your repository on GitHub.
3. Click **Settings** (top tab) -> Select **Pages** (left sidebar).
4. Under **Build and deployment**:
   - **Source**: `Deploy from a branch`
   - **Branch**: `main` / Folder: `/ (root)`
5. Click **Save**.
6. GitHub will publish your webpage at:
   `https://<username>.github.io/<repository-name>/`

---

## OPTION 5: Deploy to Railway

1. Go to [Railway.app](https://railway.app) and sign in.
2. Click **New Project** -> **Deploy from GitHub repo**.
3. Select your repository.
4. Railway automatically detects `railway.json` / `Dockerfile` / `Procfile` and launches the application.
5. In your project settings, click **Generate Domain** to get a public URL (`https://xxx.up.railway.app`).

---

## OPTION 6: Deploy with Docker on Any Linux Server / VPS (AWS, GCP, DigitalOcean)

If you have a Linux server (Ubuntu/Debian) or cloud VM:

### 1. Build and Run with Docker Compose:
```bash
# Clone repo on server
git clone https://github.com/<YOUR_USERNAME>/<YOUR_REPO>.git
cd <YOUR_REPO>

# Start container in detached mode
docker compose up -d --build
```

### 2. Verify Container Health:
```bash
docker ps
curl http://localhost:8000/healthz
```

### 3. Open in Browser:
Visit `http://<YOUR_SERVER_PUBLIC_IP>:8000`

---

## Health Check & API Verification

Once deployed on any server, verify the live endpoints:
- **Web UI**: `https://<YOUR-URL>/`
- **Health Probe**: `https://<YOUR-URL>/healthz` (Returns `{"status": "healthy"}`)
- **Data API**: `https://<YOUR-URL>/api/data`
