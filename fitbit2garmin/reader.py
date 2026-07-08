"""Read and parse Fitbit export JSON files."""

import json
import logging
import os
import re
from datetime import datetime, date, timedelta
from typing import Optional

from .models import (
    Activity, DailySummary, FitbitData, HeartRateSample,
    SleepSession, WeightLog,
)

logger = logging.getLogger(__name__)

FITBIT_SPORT_MAP = {
    90009: "Running",
    90010: "Walking",
    90011: "Hiking",
    90012: "Treadmill",
    90013: "Cycling",
    90014: "Stationary Biking",
    90015: "Swimming",
    90016: "Elliptical",
    90017: "Weights",
    90018: "Yoga",
    90019: "Tennis",
    90020: "Basketball",
    90021: "Football",
    90022: "Golf",
    90023: "Martial Arts",
    90024: "Pilates",
    90025: "Stretching",
    90026: "Stair Climbing",
    90027: "Meditation",
    90028: "Cardio",
    90029: "Circuit Training",
    90030: "Dancing",
    90031: "Tai Chi",
    90032: "CrossFit",
    90033: "HIIT",
    90034: "Running",
    90035: "Walking",
    90036: "Cycling",
    90037: "Swimming",
    90038: "Hiking",
    90039: "Elliptical",
}

FITBIT_SPORT_NAME_MAP = {
    "Run": "Running",
    "Walk": "Walking",
    "Hike": "Hiking",
    "Bike": "Biking",
    "Cycling": "Biking",
    "Swim": "Swimming",
    "Swimming": "Swimming",
    "Elliptical": "Elliptical",
    "Weights": "Strength",
    "Strength": "Strength",
    "Yoga": "Yoga",
    "Treadmill": "Running",
    "Spinning": "Biking",
    "Walk (outdoor)": "Walking",
    "Run (outdoor)": "Running",
    "Outdoor Bike": "Biking",
    "Outdoor Run": "Running",
    "Outdoor Walk": "Walking",
    "Sport": "Other",
    "Workout": "Other",
    "Exercise": "Other",
    "Activity": "Other",
}


_HR_DATE_FORMATS = [
    "%m/%d/%y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%m/%d/%Y %H:%M:%S",
]


def _parse_hr_datetime(s: str) -> Optional[datetime]:
    for fmt in _HR_DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _parse_fitbit_date(s: str) -> Optional[date]:
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        pass
    try:
        return datetime.strptime(s[:10], "%m/%d/%Y").date()
    except ValueError:
        pass
    return None


def _parse_fitbit_datetime(s: str) -> Optional[datetime]:
    if not s:
        return None
    for fmt in [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%m/%d/%y %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
    ]:
        try:
            return datetime.strptime(s[:19], fmt)
        except ValueError:
            continue
    return None


def _get_type_sport(activity_name: str, activity_type_id: Optional[int] = None) -> str:
    if activity_type_id and activity_type_id in FITBIT_SPORT_MAP:
        return FITBIT_SPORT_MAP[activity_type_id]
    if activity_name:
        upper = activity_name.strip().lower()
        for key, sport in FITBIT_SPORT_NAME_MAP.items():
            if key.lower() == upper or upper.startswith(key.lower()):
                return sport
        if "run" in upper:
            return "Running"
        if "walk" in upper:
            return "Walking"
        if "bike" in upper or "cycl" in upper:
            return "Biking"
        if "swim" in upper:
            return "Swimming"
        if "hike" in upper:
            return "Hiking"
        if "yoga" in upper:
            return "Yoga"
        if "strength" in upper or "weight" in upper or "lift" in upper:
            return "Strength"
        if "elliptical" in upper:
            return "Elliptical"
        if "cardio" in upper:
            return "Other"
    return "Other"


def find_files(root_dir: str) -> dict[str, list[str]]:
    """Scan the export directory and group files by data type."""
    files: dict[str, set[str]] = {}
    for dirpath, _, filenames in os.walk(root_dir):
        for f in filenames:
            if not f.endswith(".json"):
                continue
            full = os.path.join(dirpath, f)
            lower = f.lower()
            if lower.startswith("heart_rate") or lower.startswith("heart-rate"):
                files.setdefault("heart_rate", set()).add(full)
            elif lower.startswith("sleep"):
                files.setdefault("sleep", set()).add(full)
            elif lower.startswith("activities") or lower.startswith("physical_activity"):
                files.setdefault("activities", set()).add(full)
            elif lower.startswith("steps"):
                files.setdefault("steps", set()).add(full)
            elif lower.startswith("calories"):
                files.setdefault("calories", set()).add(full)
            elif lower.startswith("distance"):
                files.setdefault("distance", set()).add(full)
            elif lower.startswith("weight"):
                files.setdefault("weight", set()).add(full)
            elif lower.startswith("body") and "fat" not in lower:
                files.setdefault("weight", set()).add(full)
    return {k: sorted(v) for k, v in files.items()}


def _load_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Failed to load %s: %s", path, e)
        return None


def read_heart_rate(file_paths: list[str]) -> list[HeartRateSample]:
    samples: list[HeartRateSample] = []
    for fp in file_paths:
        data = _load_json(fp)
        if data is None:
            continue
        if isinstance(data, list):
            for entry in data:
                if not isinstance(entry, dict):
                    continue
                dt_str = entry.get("dateTime", "")
                val = entry.get("value", {})
                if isinstance(val, dict):
                    bpm = val.get("bpm", 0)
                    conf = val.get("confidence", 0)
                else:
                    bpm = int(val) if val else 0
                    conf = 0
                ts = _parse_hr_datetime(dt_str)
                if ts and bpm:
                    samples.append(HeartRateSample(ts, int(bpm), int(conf)))
        elif isinstance(data, dict):
            hr_list = data.get("activities-heart", [])
            for entry in hr_list:
                if not isinstance(entry, dict):
                    continue
                dt_str = entry.get("dateTime", "")
                val = entry.get("value", {})
                if isinstance(val, dict):
                    rhr = val.get("restingHeartRate")
                    for zone in val.get("heartRateZones", []):
                        if isinstance(zone, dict):
                            pass
    logger.info("Read %d heart rate samples", len(samples))
    return samples


def read_sleep(file_paths: list[str]) -> list[SleepSession]:
    sessions: list[SleepSession] = []
    for fp in file_paths:
        data = _load_json(fp)
        if data is None:
            continue
        sleep_list = None
        if isinstance(data, list):
            sleep_list = data
        elif isinstance(data, dict):
            sleep_list = data.get("sleep", [])
        if not sleep_list:
            continue
        for entry in sleep_list:
            if not isinstance(entry, dict):
                continue
            try:
                dos = _parse_fitbit_date(entry.get("dateOfSleep", ""))
                if not dos:
                    continue
                dur = entry.get("duration", 0) or 0
                st_str = entry.get("startTime", "")
                et_str = entry.get("endTime", "")
                st = _parse_fitbit_datetime(st_str) if st_str else None
                et = _parse_fitbit_datetime(et_str) if et_str else None
                if not st or not et:
                    continue
                levels = entry.get("levels", {}) or {}
                summary = levels.get("summary", {}) or {}
                if isinstance(summary, list):
                    summary = {}
                has_summary = bool(summary)
                minutes_asleep = 0
                minutes_awake = 0
                if has_summary:
                    asleep_total = 0
                    for level_name, level_info in summary.items():
                        if isinstance(level_info, dict):
                            mins = level_info.get("minutes", 0)
                            if level_name == "asleep":
                                asleep_total = mins
                            elif level_name == "wake":
                                minutes_awake += mins
                    if asleep_total:
                        minutes_asleep = asleep_total
                    else:
                        for level_name, level_info in summary.items():
                            if isinstance(level_info, dict):
                                mins = level_info.get("minutes", 0)
                                if level_name in ("deep", "light", "rem"):
                                    minutes_asleep += mins
                if not minutes_asleep:
                    minutes_asleep = entry.get("minutesAsleep", 0) or 0
                if not minutes_awake:
                    minutes_awake = entry.get("minutesAwake", 0) or 0
                ses = SleepSession(
                    date=dos,
                    start_time=st,
                    end_time=et,
                    duration_millis=dur,
                    efficiency=entry.get("efficiency", 0) or 0,
                    minutes_asleep=minutes_asleep,
                    minutes_awake=minutes_awake,
                    minutes_to_fall_asleep=entry.get("minutesToFallAsleep", 0) or 0,
                    time_in_bed=entry.get("timeInBed", 0) or 0,
                    levels_data=levels.get("data", []) or [],
                    summary=summary,
                    is_main_sleep=entry.get("isMainSleep", True),
                )
                sessions.append(ses)
            except Exception as e:
                logger.debug("Error parsing sleep entry: %s", e)
                continue
    logger.info("Read %d sleep sessions", len(sessions))
    return sessions


def read_weight(file_paths: list[str]) -> list[WeightLog]:
    logs: list[WeightLog] = []
    for fp in file_paths:
        data = _load_json(fp)
        if data is None:
            continue
        entries = data if isinstance(data, list) else data.get("body", data.get("weight", []))
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            try:
                dt_str = entry.get("dateTime", "")
                val = entry.get("value", entry)
                if isinstance(val, dict):
                    weight = float(val.get("weight", 0) or 0)
                    bmi = float(val.get("bmi", 0) or 0)
                    fat = float(val.get("fat", 0)) if val.get("fat") else None
                else:
                    weight = float(entry.get("weight", 0) or 0)
                    bmi = float(entry.get("bmi", 0) or 0)
                    fat = float(entry.get("fat", 0)) if entry.get("fat") else None
                if not weight:
                    continue
                dt = _parse_fitbit_datetime(dt_str) if " " in dt_str or "T" in dt_str else None
                if not dt:
                    dt = datetime.strptime(dt_str[:10], "%Y-%m-%d") if dt_str[:10] else None
                if not dt:
                    continue
                logs.append(WeightLog(date=dt, weight_kg=weight, bmi=bmi, body_fat_pct=fat))
            except (ValueError, TypeError) as e:
                logger.debug("Error parsing weight entry: %s", e)
                continue
    logger.info("Read %d weight logs", len(logs))
    return logs


def read_activities(file_paths: list[str]) -> list[Activity]:
    activities: list[Activity] = []
    for fp in file_paths:
        data = _load_json(fp)
        if data is None:
            continue
        entries = data if isinstance(data, list) else data.get("activities", data.get("physical_activity", []))
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            try:
                name = entry.get("activityName", "") or ""
                type_id = entry.get("activityTypeId")
                sport = _get_type_sport(name, type_id)
                start_str = entry.get("startTime", "")
                st = _parse_fitbit_datetime(start_str) if start_str else None
                if not st:
                    continue
                active_dur = entry.get("activeDuration", 0) or 0
                orig_dur = entry.get("originalDuration", 0) or 0
                dur_s = (active_dur if active_dur > orig_dur else orig_dur) / 1000.0
                if dur_s <= 0:
                    continue
                calories = entry.get("calories", 0) or 0
                distance = float(entry.get("distance", 0) or 0)
                steps = entry.get("steps", 0) or 0
                hr_zones = entry.get("heartRateZones", []) or []
                avg_hr = None
                max_hr = None
                for zone in hr_zones:
                    if isinstance(zone, dict):
                        zname = (zone.get("name") or "").lower()
                        if "peak" in zname or "cardio" in zname:
                            max_val = zone.get("max", 0)
                            if max_val and (max_hr is None or max_val > max_hr):
                                max_hr = int(max_val)
                hrr = entry.get("heartRate")
                if isinstance(hrr, dict):
                    avg_hr = hrr.get("average")
                    if not max_hr:
                        max_hr = hrr.get("max")
                act = Activity(
                    name=name or sport,
                    sport=sport,
                    start_time=st,
                    duration_seconds=dur_s,
                    calories=int(calories),
                    distance_meters=distance,
                    steps=int(steps),
                    avg_heart_rate=avg_hr,
                    max_heart_rate=max_hr,
                )
                activities.append(act)
            except Exception as e:
                logger.debug("Error parsing activity entry: %s", e)
                continue
    logger.info("Read %d activities", len(activities))
    return activities


def _read_daily_field(file_paths: list[str], field_name: str):
    """Read daily summary arrays like steps, calories, distance."""
    results: dict[date, float] = {}
    for fp in file_paths:
        data = _load_json(fp)
        if data is None:
            continue
        key = f"activities-{field_name}"
        entries = data if isinstance(data, list) else data.get(key, [])
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            dt_str = entry.get("dateTime", "")
            d = _parse_fitbit_date(dt_str)
            val_str = entry.get("value", "0")
            try:
                val = float(val_str)
            except (ValueError, TypeError):
                val = 0
            if d is not None:
                if d not in results:
                    results[d] = 0
                results[d] += val
    return results


def read_daily_summaries(files: dict[str, list[str]]) -> list[DailySummary]:
    steps = _read_daily_field(files.get("steps", []), "steps")
    calories = _read_daily_field(files.get("calories", []), "calories")
    distance = _read_daily_field(files.get("distance", []), "distance")
    all_dates = set(steps.keys()) | set(calories.keys()) | set(distance.keys())
    summaries: list[DailySummary] = []
    for d in sorted(all_dates):
        summaries.append(DailySummary(
            date=d,
            steps=int(steps.get(d, 0)),
            calories=calories.get(d, 0),
            distance_meters=distance.get(d, 0),
        ))
    logger.info("Built %d daily summaries", len(summaries))
    return summaries


def read_all(root_dir: str) -> FitbitData:
    """Read all Fitbit data from an export directory."""
    found = find_files(root_dir)
    logger.info("Found %d file categories in %s", len(found), root_dir)
    for cat, paths in found.items():
        logger.debug("  %s: %d files", cat, len(paths))
    data = FitbitData(
        activities=read_activities(found.get("activities", [])),
        heart_rate_samples=read_heart_rate(found.get("heart_rate", [])),
        sleep_sessions=read_sleep(found.get("sleep", [])),
        weight_logs=read_weight(found.get("weight", [])),
        daily_summaries=read_daily_summaries(found),
    )
    return data
