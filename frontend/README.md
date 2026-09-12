# SCOUT Frontend

React + TypeScript + Tailwind dashboard for the drone-based emergency coordination system.

## Develop

```bash
npm install
npm run dev
```

Copy `.env.example` to `.env`. The hackathon configuration calls FastAPI at
`http://10.50.12.164:8081`; update the IP if the GB10 address changes. Port
`5173` serves this webpage, while port `8081` serves the backend API.

The dashboard does not substitute fake incidents when the backend is
unreachable. It shows a disconnected warning instead. `VITE_OPERATOR_ID`
identifies review, allocation, and station-resource changes in the audit log.

## Build

```bash
npm run build
```
