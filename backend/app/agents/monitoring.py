from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.db import get_database
from app.repositories.collections import assessment_repo, assignment_repo, detection_repo, log_repo
from app.repositories.collections import incident_repo
from app.schemas.log import LogEntry
from app.utils.ids import generate_id


class MonitoringAgent:
    """Agent 5. Append-only log of everything that happens, plus final
    per-incident report assembly on resolution. In the full async design
    this agent watches every write to the shared store; in this synchronous
    hackathon pipeline, each pipeline step calls `log()` explicitly at the
    point a state change happens."""

    async def log(
        self,
        event_type: str,
        summary: str,
        incident_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        actor_type: str = "system",
        actor_id: Optional[str] = None,
    ) -> LogEntry:
        now = datetime.now(timezone.utc)
        entry = LogEntry(
            log_id=generate_id("log", now),
            timestamp=now,
            incident_id=incident_id,
            actor_type=actor_type,
            actor_id=actor_id,
            event_type=event_type,
            summary=summary,
            payload=payload or {},
        )
        await log_repo.insert(entry)
        return entry

    async def compile_report(self, incident_id: str) -> Dict[str, Any]:
        incident = await incident_repo.get(incident_id)
        detections = await detection_repo.list({}, sort_field="timestamp")
        assessments = await assessment_repo.list({"incident_id": incident_id}, sort_field="timestamp")
        assignments = await assignment_repo.list({"incident_id": incident_id}, sort_field="created_at")
        detection_ids = {a.detection_id for a in assessments}
        detections = [d for d in detections if d.detection_id in detection_ids]
        logs = await log_repo.list({"incident_id": incident_id}, sort_field="timestamp")

        return {
            "incident": incident.model_dump(mode="json") if incident else None,
            "detections": [d.model_dump(mode="json") for d in detections],
            "assessments": [a.model_dump(mode="json") for a in assessments],
            "assignments": [a.model_dump(mode="json") for a in assignments],
            "timeline": [l.model_dump(mode="json") for l in reversed(logs)],
        }

    async def save_report(self, incident_id: str) -> Dict[str, Any]:
        report = await self.compile_report(incident_id)
        now = datetime.now(timezone.utc)
        doc = {
            "report_id": generate_id("rpt", now),
            "incident_id": incident_id,
            "generated_at": now.isoformat(),
            **report,
        }
        await get_database()["reports"].insert_one(doc)
        doc.pop("_id", None)
        return doc


monitoring_agent = MonitoringAgent()
