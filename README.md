# Local Drone Emergency Coordination Demo

This FastAPI backend accepts structured output from the Perception and Triage
agents, records incidents in MongoDB, recommends station resources, and keeps an
audit trail. It is designed for the Dell GB10 and uses only the local Nemotron
endpoint. It never sends a real emergency notification or calls 911.

## Safety rules

- Every allocation starts in `awaiting_approval`.
- A named human operator must approve or reject an allocation.
- The notification route is a simulation and performs no external action.
- Confidence below `0.70` always requires human review.
- The Nemotron helper rejects non-loopback model URLs, preventing remote LLM use.

## GB10 startup

MongoDB and Nemotron must already be running on the GB10. From the repository:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --host 0.0.0.0 --port 8081
```

The API documentation is then available at `http://GB10-IP:8081/docs`. Keep
MongoDB and Nemotron bound to `127.0.0.1`; only expose the backend API to the
team network.

## Agent handoff contract

`POST /agent-handoff` is the main integration route. Send the agreed Perception
and Triage JSON objects in one request:

```json
{
  "perception": {
    "detection_id": "det-demo-1",
    "timestamp": "2026-09-12T16:00:00Z",
    "location": {"latitude": 40.7128, "longitude": -74.0060},
    "human_detected": true,
    "number_of_people": 1,
    "injury_status": "unknown",
    "visible_hazards": ["debris"],
    "observations": "One person is visible near debris.",
    "confidence": 0.86
  },
  "triage": {
    "urgency": "medium",
    "incident_type": "person_near_hazard",
    "location": {"latitude": 40.7128, "longitude": -74.0060},
    "observations": "A person is close to a visible hazard.",
    "reasoning": "Human review should confirm the scene.",
    "confidence": 0.81,
    "needs_human_verification": true
  }
}
```

The response includes the stored detection, assessment, incident, recommended
allocation, and any validation warnings.

## Human approval flow

1. Propose again if needed: `POST /incidents/{incident_id}/allocation`
2. Approve or reject: `POST /allocations/{assignment_id}/decision`
3. Run the safe demo notification: `POST /allocations/{assignment_id}/notify`
4. Inspect history: `GET /incidents/{incident_id}/timeline`
5. Generate summary: `GET /incidents/{incident_id}/final-report`

Station registration and updates require an `X-Operator-ID` request header so
changes are attributable in the audit log.

## Verification

```bash
PYTHONPATH=backend python3 -m unittest discover -s backend/tests -v
curl -s http://127.0.0.1:8081/health
curl -s http://127.0.0.1:8081/readiness
curl -s http://127.0.0.1:8000/v1/models
docker exec emergency-mongodb mongosh --quiet --eval 'db.runCommand({ping:1})'
```

Before the demo, disconnect external internet and repeat the health and handoff
tests to prove the runtime is fully local.

## Frontend

Create `frontend/.env` from the example. Port `5173` serves the webpage; port
`8081` is the FastAPI backend that the webpage calls.

```bash
cd frontend
cp .env.example .env
npm ci
npm run dev -- --host 0.0.0.0
```

The dashboard never substitutes fake incidents when the backend is offline.
Human observation review, allocation approval, and simulated notification are
separate actions, and operator actions are recorded as `VITE_OPERATOR_ID`.

Pitch deck:
https://docs.google.com/presentation/d/1oh6wpRUXGpdKC5UVbTl_9v0xvNj2zqti9dBFHKbfw5w/edit
