import os


class Settings:
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    mongodb_db_name: str = os.getenv("MONGODB_DB_NAME", "drone_ecs")

    # Confidence below this forces needs_human_verification on an assessment.
    confidence_threshold: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.6"))

    # Incident dedup: a new detection is folded into an existing open incident
    # instead of creating a new one when it falls within both windows below.
    dedup_distance_meters: float = float(os.getenv("DEDUP_DISTANCE_METERS", "75"))
    dedup_time_window_minutes: float = float(os.getenv("DEDUP_TIME_WINDOW_MINUTES", "30"))

    # Emergency Coordinator (Agent 3) thresholds.
    multi_station_people_threshold: int = int(os.getenv("MULTI_STATION_PEOPLE_THRESHOLD", "4"))

    media_root: str = os.getenv("MEDIA_ROOT", "media")


settings = Settings()
