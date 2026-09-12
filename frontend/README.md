# SCOUT Frontend

React + TypeScript + Tailwind dashboard for the drone-based emergency coordination system.

## Develop

```bash
npm install
npm run dev
```

By default the app calls the FastAPI backend at `http://localhost:8000`. Copy
`.env.example` to `.env` and set `VITE_API_BASE_URL` to point elsewhere. If the
backend isn't reachable, the dashboard falls back to demo data so the UI still
renders.

## Build

```bash
npm run build
```
