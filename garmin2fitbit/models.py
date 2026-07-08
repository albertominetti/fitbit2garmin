from dataclasses import dataclass, field
from datetime import datetime, date


@dataclass
class HeartRateSample:
    timestamp: datetime
    bpm: int


@dataclass
class Activity:
    name: str
    sport: str
    start_time: datetime
    duration_seconds: float
    calories: int = 0
    distance_meters: float = 0
    steps: int = 0
    heart_rate_samples: list[HeartRateSample] = field(default_factory=list)
    avg_heart_rate: int | None = None
    max_heart_rate: int | None = None


@dataclass
class SleepSession:
    date: date
    start_time: datetime
    end_time: datetime
    duration_millis: int
    minutes_asleep: int = 0
    minutes_awake: int = 0
    efficiency: int = 0
    time_in_bed: int = 0
    minutes_to_fall_asleep: int = 0


@dataclass
class WeightLog:
    date: datetime
    weight_kg: float
    bmi: float = 0
    body_fat_pct: float | None = None


@dataclass
class DailySummary:
    date: date
    steps: int = 0
    calories: float = 0
    distance_meters: float = 0
    active_minutes: int = 0
    sedentary_minutes: int = 0
    floors: int = 0


@dataclass
class GarminData:
    activities: list[Activity] = field(default_factory=list)
    sleep_sessions: list[SleepSession] = field(default_factory=list)
    weight_logs: list[WeightLog] = field(default_factory=list)
    daily_summaries: list[DailySummary] = field(default_factory=list)
