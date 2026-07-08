"""Read and parse Garmin data export files (TCX, CSV)."""

import csv
import logging
import os
import xml.etree.ElementTree as ET
from datetime import datetime, date, timedelta

from .models import (
    Activity, DailySummary, GarminData, HeartRateSample,
    SleepSession, WeightLog,
)

logger = logging.getLogger(__name__)

TCX_NS = "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"

GARMIN_SPORT_MAP = {
    "Running": "Running",
    "Walking": "Walking",
    "Cycling": "Biking",
    "Biking": "Biking",
    "Other": "Other",
    "Hiking": "Hiking",
    "Swimming": "Swimming",
}


def _parse_tcx_datetime(s: str) -> datetime:
    s = s.replace("Z", "+00:00")
    if s.endswith("+00:00"):
        s = s[:-6]
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(s[:19], fmt[:19])
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: {s}")


def _get_text(el, tag: str, ns: str = TCX_NS) -> str | None:
    found = el.find(f"{{{ns}}}{tag}")
    return found.text if found is not None and found.text else None


def read_tcx(filepath: str) -> Activity | None:
    """Parse a single Garmin TCX file into an Activity."""
    try:
        tree = ET.parse(filepath)
    except Exception as e:
        logger.debug("Failed to parse TCX %s: %s", filepath, e)
        return None

    root = tree.getroot()
    ns = TCX_NS

    activities_el = root.find(f".//{{{ns}}}Activities")
    if activities_el is None:
        activities_el = root.find(f".//{{{ns}}}Activity/..")

    act_el = root.find(f".//{{{ns}}}Activity")
    if act_el is None:
        return None

    sport = act_el.get("Sport", "Other")
    sport = GARMIN_SPORT_MAP.get(sport, "Other")

    # activity ID = start time
    id_el = act_el.find(f"{{{ns}}}Id")
    if id_el is None or not id_el.text:
        return None
    start_time = _parse_tcx_datetime(id_el.text)

    # first Lap
    lap = act_el.find(f"{{{ns}}}Lap")
    if lap is None:
        return None

    duration_s = float(_get_text(lap, "TotalTimeSeconds") or 0)
    if duration_s <= 0:
        return None

    distance_m = float(_get_text(lap, "DistanceMeters") or 0)
    calories = int(float(_get_text(lap, "Calories") or 0))

    avg_hr = None
    max_hr = None
    avg_hr_el = lap.find(f"{{{ns}}}AverageHeartRateBpm")
    if avg_hr_el is not None:
        val = _get_text(avg_hr_el, "Value")
        if val:
            avg_hr = int(val)

    max_hr_el = lap.find(f"{{{ns}}}MaximumHeartRateBpm")
    if max_hr_el is not None:
        val = _get_text(max_hr_el, "Value")
        if val:
            max_hr = int(val)

    # Trackpoints
    samples: list[HeartRateSample] = []
    total_cadence = 0
    cadence_count = 0
    track = lap.find(f"{{{ns}}}Track")
    if track is not None:
        for tp in track.findall(f"{{{ns}}}Trackpoint"):
            time_el = tp.find(f"{{{ns}}}Time")
            if time_el is None or not time_el.text:
                continue
            ts = _parse_tcx_datetime(time_el.text)

            bpm = None
            hr_el = tp.find(f"{{{ns}}}HeartRateBpm")
            if hr_el is not None:
                val = _get_text(hr_el, "Value")
                if val:
                    bpm = int(val)

            cad_el = tp.find(f"{{{ns}}}Cadence")
            if cad_el is not None and cad_el.text:
                try:
                    total_cadence += int(cad_el.text)
                    cadence_count += 1
                except ValueError:
                    pass

            if bpm is not None:
                samples.append(HeartRateSample(ts, bpm))

    # derive steps from average cadence × duration
    steps = 0
    if cadence_count > 0:
        avg_cadence = total_cadence / cadence_count
        steps = int(avg_cadence * (duration_s / 60))

    name = f"{sport} {start_time.strftime('%Y-%m-%d %H:%M')}"
    return Activity(
        name=name,
        sport=sport,
        start_time=start_time,
        duration_seconds=duration_s,
        calories=calories,
        distance_meters=distance_m,
        steps=steps,
        heart_rate_samples=samples,
        avg_heart_rate=avg_hr,
        max_heart_rate=max_hr,
    )


def read_activities_from_tcx(directory: str) -> list[Activity]:
    """Scan a directory for TCX files and parse them."""
    activities: list[Activity] = []
    for fname in sorted(os.listdir(directory)):
        if not fname.lower().endswith(".tcx"):
            continue
        fpath = os.path.join(directory, fname)
        act = read_tcx(fpath)
        if act:
            activities.append(act)
    logger.info("Read %d activities from TCX files", len(activities))
    return activities


def read_weight_csv(filepath: str) -> list[WeightLog]:
    """Read Garmin body composition CSV.

    Expected header: Date,Weight,BMI,BodyFat,BoneMass,MuscleMass,BodyWater
    """
    logs: list[WeightLog] = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                date_str = row.get("Date", "").strip()
                if not date_str:
                    continue
                try:
                    dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
                except ValueError:
                    continue
                weight = _float_or(row.get("Weight"), 0)
                if weight <= 0:
                    continue
                bmi = _float_or(row.get("BMI"), 0)
                fat = _float_or(row.get("BodyFat"), None)
                logs.append(WeightLog(
                    date=dt, weight_kg=weight, bmi=bmi, body_fat_pct=fat,
                ))
    except FileNotFoundError:
        pass
    logger.info("Read %d weight logs from CSV", len(logs))
    return logs


def read_sleep_csv(filepath: str) -> list[SleepSession]:
    """Read Garmin sleep CSV.

    Expected header: Date,Sleep Start,Sleep End,Duration (min),...
    or: Date,Start Time,End Time,Duration,Minutes Asleep,...
    """
    sessions: list[SleepSession] = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                date_str = row.get("Date", "").strip()
                if not date_str:
                    continue
                try:
                    d = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
                except ValueError:
                    continue

                start_str = (row.get("Sleep Start") or row.get("Start Time") or "").strip()
                end_str = (row.get("Sleep End") or row.get("End Time") or "").strip()
                if not start_str or not end_str:
                    continue

                start_time = _parse_sleep_dt(date_str[:10], start_str)
                end_time = _parse_sleep_dt(date_str[:10], end_str)
                if not start_time or not end_time:
                    continue

                dur_raw = int(_float_or(row.get("Duration (min)") or row.get("Duration"), 0))
                dur_millis = dur_raw * 60000

                mins_asleep = int(_float_or(
                    row.get("Minutes Asleep") or row.get("Sleep Time (min)"), 0
                ))
                mins_awake = int(_float_or(
                    row.get("Minutes Awake") or row.get("Awake Time (min)"), 0
                ))

                sessions.append(SleepSession(
                    date=d,
                    start_time=start_time,
                    end_time=end_time,
                    duration_millis=dur_millis or int((end_time - start_time).total_seconds() * 1000),
                    minutes_asleep=mins_asleep,
                    minutes_awake=mins_awake,
                ))
    except FileNotFoundError:
        pass
    logger.info("Read %d sleep sessions from CSV", len(sessions))
    return sessions


def read_daily_summary_csv(filepath: str) -> list[DailySummary]:
    """Read Garmin daily summary CSV.

    Common Garmin export header:
      Date,Steps,Calories,Distance,Floors,Minutes Sedentary,...
    """
    summaries: list[DailySummary] = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                date_str = row.get("Date", "").strip()
                if not date_str:
                    continue
                try:
                    d = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
                except ValueError:
                    continue
                steps = int(_float_or(row.get("Steps"), 0))
                calories = _float_or(row.get("Calories"), 0)
                dist = _float_or(row.get("Distance"), 0)
                floors = int(_float_or(row.get("Floors"), 0))
                sed = int(_float_or(row.get("Minutes Sedentary"), 0))
                active = int(_float_or(
                    row.get("Minutes Lightly Active") or row.get("Active Minutes"), 0
                ))
                summaries.append(DailySummary(
                    date=d, steps=steps, calories=calories,
                    distance_meters=dist, floors=floors,
                    sedentary_minutes=sed, active_minutes=active,
                ))
    except FileNotFoundError:
        pass
    logger.info("Read %d daily summaries from CSV", len(summaries))
    return summaries


def _float_or(val, default):
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _parse_sleep_dt(date_part: str, time_part: str) -> datetime | None:
    time_part = time_part.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%H:%M:%S", "%H:%M"):
        try:
            if ":" in time_part and len(time_part) <= 5:
                return datetime.strptime(f"{date_part} {time_part}", "%Y-%m-%d %H:%M")
            return datetime.strptime(time_part[:19], fmt)
        except ValueError:
            continue
    return None


def find_csv_files(root_dir: str) -> dict[str, str]:
    """Find Garmin CSV export files by naming pattern."""
    result: dict[str, str] = {}
    for fname in os.listdir(root_dir):
        if not fname.lower().endswith(".csv"):
            continue
        fpath = os.path.join(root_dir, fname)
        lower = fname.lower()
        if "body" in lower or "weight" in lower or "composit" in lower:
            result["body"] = fpath
        elif "sleep" in lower:
            result["sleep"] = fpath
        elif "daily" in lower or "summary" in lower or "steps" in lower:
            result["daily"] = fpath
    return result


def read_all(root_dir: str) -> GarminData:
    """Read all Garmin data from a directory."""
    data = GarminData()

    tcx_dir = os.path.join(root_dir, "activities")
    if os.path.isdir(tcx_dir):
        data.activities = read_activities_from_tcx(tcx_dir)

    csv_files = find_csv_files(root_dir)
    if "body" in csv_files:
        data.weight_logs = read_weight_csv(csv_files["body"])
    if "sleep" in csv_files:
        data.sleep_sessions = read_sleep_csv(csv_files["sleep"])
    if "daily" in csv_files:
        data.daily_summaries = read_daily_summary_csv(csv_files["daily"])

    logger.info(
        "Found: %d activities, %d sleep sessions, %d weight logs, %d daily summaries",
        len(data.activities), len(data.sleep_sessions),
        len(data.weight_logs), len(data.daily_summaries),
    )
    return data
