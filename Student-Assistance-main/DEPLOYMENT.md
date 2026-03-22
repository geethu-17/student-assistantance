# Public Hosting Guide (Railway + Vercel)

This project is configured for free-friendly public hosting using:
- Backend: Railway
- Frontend: Vercel

## 1) Prerequisites
- Push your repository to GitHub.
- Keep backend secrets ready (`MONGO_URI`, `SMTP_*`, etc.).

## 2) Deploy Backend on Railway
1. Open Railway and click `New Project` -> `Deploy from GitHub Repo`.
2. Select repository: `Student-Assistance`.
3. Open the created service -> `Settings` -> `Root Directory`.
4. Set root directory to:
`student-support-backend`
5. Confirm start command is:
`gunicorn --bind 0.0.0.0:$PORT app:app`
6. Redeploy the service.

## 3) Set Backend Environment Variables (Railway)
Add these variables in Railway service settings:
- `MONGO_URI`
- `MONGO_DB_NAME`
- `MONGO_SERVER_SELECTION_TIMEOUT_MS` (optional, default `15000`)
- `MONGO_CONNECT_TIMEOUT_MS` (optional, default `10000`)
- `MONGO_SOCKET_TIMEOUT_MS` (optional, default `10000`)
- `ADMIN_TOKEN_SECRET`
- `ADMIN_TOKEN_SALT` (optional)
- `ADMIN_TOKEN_EXPIRES_SECONDS` (optional)
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`
- `SMTP_USE_TLS`
- `SMTP_USE_SSL`
- `FRONTEND_BASE_URL` (set this after Vercel deploy)
- `TELEGRAM_BOT_TOKEN` (optional)
- `TELEGRAM_WEBHOOK_SECRET` (optional)
- `WHATSAPP_ACCESS_TOKEN` (optional)
- `WHATSAPP_PHONE_NUMBER_ID` (optional)
- `WHATSAPP_VERIFY_TOKEN` (optional)
- `INSTAGRAM_ACCESS_TOKEN` (optional)
- `INSTAGRAM_BUSINESS_ACCOUNT_ID` (optional)
- `INSTAGRAM_VERIFY_TOKEN` (optional)

## 4) Deploy Frontend on Vercel
1. Open Vercel -> `Add New...` -> `Project`.
2. Import repository: `Student-Assistance`.
3. Set `Root Directory` to:
`student-support-frontend`
4. Use build settings:
- Build Command: `npm run build`
- Output Directory: `dist`
5. Add environment variable:
- `VITE_API_BASE_URL=https://<your-railway-backend-domain>/api`
6. Deploy.

## 5) Final Link-Up
1. Copy your Vercel URL.
2. In Railway, set:
- `FRONTEND_BASE_URL=https://<your-vercel-domain>`
3. Redeploy backend once.

## 6) Verification
- Frontend: `https://<your-vercel-domain>`
- Backend health: `https://<your-railway-domain>/`
- Backend DB status: `https://<your-railway-domain>/api/db-status`

## Optional: Local Docker Deployment
If you want local container deployment instead of public hosting:

```bash
docker compose up --build -d
```

Useful commands:

```bash
docker compose logs -f
docker compose restart backend
docker compose restart frontend
docker compose down
```
