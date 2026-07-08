"""Write converted data to Fitbit-compatible JSON formats."""

import json
import logging
import os
import xml.etree.ElementTree as ET
from datetime import timedelta

from .models import Activity, DailySummary, GarminData, SleepSession, WeightLog

logger = logging.getLogger(__name__)

# Garmin sport → Fitbit activity type ID
FITBIT_TYPE_MAP = {
    "Running": 90009,
    "Walking": 90010,
    "Hiking": 90011,
    "Biking": 90013,
    "Cycling": 90013,
    "Swimming": 90015,
    "Elliptical": 90016,
    "Weights": 90017,
    "Strength": 90017,
    "Yoga": 90018,
    "Cardio": 90028,
    "Other": 90028,
}


def _compute_hr_zones(bpms: list[int]) -> list[dict]:
    """Compute approximate Fitbit-style heart rate zones."""
    if not bpms:
        return []
    max_hr = max(bpms)
    zone_map = {
        "Out of Range": (0, 94),
        "Fat Burn": (95, 134),
        "Cardio": (135, 159),
        "Peak": (160, max(max_hr, 160)),
    }
    zones = []
    for name, (lo, hi) in zone_map.items():
        zone_vals = [b for b in bpms if lo <= b <= hi]
        zones.append({
            "name": name,
            "min": lo,
            "max": hi if hi < 250 else max_hr,
            "minutes": len(zone_vals),
            "caloriesOut": 0,
        })
    return zones


def _activity_to_fitbit(act: Activity) -> dict:
    start_str = act.start_time.strftime("%Y-%m-%dT%H:%M:%S.000")
    dur_ms = int(act.duration_seconds * 1000)
    bpms = [s.bpm for s in act.heart_rate_samples if s.bpm > 0]
    return {
        "activityName": act.name,
        "activityTypeId": FITBIT_TYPE_MAP.get(act.sport, 90028),
        "activeDuration": dur_ms,
        "calories": act.calories,
        "distance": act.distance_meters,
        "distanceUnit": "METERS",
        "steps": act.steps,
        "startTime": start_str,
        "duration": dur_ms,
        "heartRateZones": _compute_hr_zones(bpms),
        "originalDuration": dur_ms,
        "originalStartTime": start_str,
        "logType": "auto",
        "heartRate": (
            {"average": act.avg_heart_rate, "max": act.max_heart_rate}
            if act.avg_heart_rate or act.max_heart_rate
            else None
        ),
    }


def _weight_to_fitbit(log: WeightLog) -> dict:
    val: dict = {"weight": log.weight_kg, "bmi": log.bmi}
    if log.body_fat_pct is not None:
        val["fat"] = log.body_fat_pct
    return {
        "dateTime": log.date.strftime("%Y-%m-%d"),
        "value": val,
    }


def _sleep_to_fitbit(ses: SleepSession) -> dict:
    return {
        "dateOfSleep": ses.date.isoformat(),
        "duration": ses.duration_millis,
        "startTime": ses.start_time.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "endTime": ses.end_time.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "minutesAsleep": ses.minutes_asleep,
        "minutesAwake": ses.minutes_awake,
        "efficiency": ses.efficiency,
        "isMainSleep": True,
        "timeInBed": ses.time_in_bed or (ses.minutes_asleep + ses.minutes_awake),
        "minutesToFallAsleep": ses.minutes_to_fall_asleep,
        "levels": {"summary": {}, "data": []},
    }


def write_activities_json(data: GarminData, output_dir: str) -> str | None:
    """Write activities as Fitbit-format JSON."""
    if not data.activities:
        return None
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, "activities.json")
    entries = [_activity_to_fitbit(a) for a in data.activities]
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({"activities": entries}, f, indent=2)
    logger.info("Wrote Fitbit activities JSON: %s (%d activities)", filepath, len(entries))
    return filepath


def write_weight_json(data: GarminData, output_dir: str) -> str | None:
    """Write weight/body data as Fitbit-format JSON."""
    if not data.weight_logs:
        return None
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, "weight.json")
    entries = [_weight_to_fitbit(w) for w in data.weight_logs]
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)
    logger.info("Wrote Fitbit weight JSON: %s (%d entries)", filepath, len(entries))
    return filepath


def write_sleep_json(data: GarminData, output_dir: str) -> str | None:
    """Write sleep data as Fitbit-format JSON."""
    if not data.sleep_sessions:
        return None
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, "sleep.json")
    entries = [_sleep_to_fitbit(s) for s in data.sleep_sessions]
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({"sleep": entries}, f, indent=2)
    logger.info("Wrote Fitbit sleep JSON: %s (%d sessions)", filepath, len(entries))
    return filepath


def write_daily_field_json(values: list[dict], output_dir: str, name: str) -> str | None:
    """Write a daily summary field (steps, calories, distance) as Fitbit-format JSON."""
    if not values:
        return None
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"activities-{name}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(values, f, indent=2)
    logger.info("Wrote Fitbit %s JSON: %s", name, filepath)
    return filepath


def write_daily_summary_json(data: GarminData, output_dir: str) -> list[str]:
    """Write daily summaries as Fitbit daily field JSON files (steps, calories, distance)."""
    if not data.daily_summaries:
        return []
    paths: list[str] = []
    steps_list = []
    calories_list = []
    distance_list = []
    for ds in data.daily_summaries:
        date_str = ds.date.isoformat()
        steps_list.append({"dateTime": date_str, "value": str(ds.steps)})
        calories_list.append({"dateTime": date_str, "value": f"{ds.calories:.1f}"})
        distance_list.append({"dateTime": date_str, "value": f"{ds.distance_meters:.1f}"})

    p = write_daily_field_json(steps_list, output_dir, "steps")
    if p:
        paths.append(p)
    p = write_daily_field_json(calories_list, output_dir, "calories")
    if p:
        paths.append(p)
    p = write_daily_field_json(distance_list, output_dir, "distance")
    if p:
        paths.append(p)

    return paths


def write_tcx_passthrough(act: Activity, output_dir: str) -> str | None:
    """Write activity as a Garmin TCX file (passthrough for Fitbit API usage)."""
    if act.duration_seconds <= 0:
        return None
    start_iso = act.start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    filename = f"{act.start_time.strftime('%Y%m%d_%H%M%S')}_{act.sport}.tcx"
    filepath = os.path.join(output_dir, filename)
    ns = "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
    ET.register_namespace("", ns)
    root = ET.Element(f"{{{ns}}}TrainingCenterDatabase")
    activities = ET.SubElement(root, f"{{{ns}}}Activities")
    act_el = ET.SubElement(activities, f"{{{ns}}}Activity")
    act_el.set("Sport", act.sport)
    act_id = ET.SubElement(act_el, f"{{{ns}}}Id")
    act_id.text = start_iso
    lap = ET.SubElement(act_el, f"{{{ns}}}Lap")
    lap.set("StartTime", start_iso)
    tt = ET.SubElement(lap, f"{{{ns}}}TotalTimeSeconds")
    tt.text = f"{act.duration_seconds:.1f}"
    dist = ET.SubElement(lap, f"{{{ns}}}DistanceMeters")
    dist.text = f"{act.distance_meters:.1f}"
    cal = ET.SubElement(lap, f"{{{ns}}}Calories")
    cal.text = str(act.calories)
    intens = ET.SubElement(lap, f"{{{ns}}}Intensity")
    intens.text = "Active"
    trig = ET.SubElement(lap, f"{{{ns}}}TriggerMethod")
    trig.text = "Manual"
    if act.avg_heart_rate:
        ha = ET.SubElement(lap, f"{{{ns}}}AverageHeartRateBpm")
        hv = ET.SubElement(ha, f"{{{ns}}}Value")
        hv.text = str(act.avg_heart_rate)
    if act.max_heart_rate:
        hm = ET.SubElement(lap, f"{{{ns}}}MaximumHeartRateBpm")
        hmv = ET.SubElement(hm, f"{{{ns}}}Value")
        hmv.text = str(act.max_heart_rate)
    track = ET.SubElement(lap, f"{{{ns}}}Track")
    if act.heart_rate_samples:
        for s in act.heart_rate_samples:
            ts = s.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
            tp = ET.Element(f"{{{ns}}}Trackpoint")
            t = ET.SubElement(tp, f"{{{ns}}}Time")
            t.text = ts
            if s.bpm:
                hr = ET.SubElement(tp, f"{{{ns}}}HeartRateBpm")
                v = ET.SubElement(hr, f"{{{ns}}}Value")
                v.text = str(s.bpm)
            track.append(tp)
    else:
        tp = ET.Element(f"{{{ns}}}Trackpoint")
        t = ET.SubElement(tp, f"{{{ns}}}Time")
        t.text = start_iso
        if act.avg_heart_rate:
            hr = ET.SubElement(tp, f"{{{ns}}}HeartRateBpm")
            v = ET.SubElement(hr, f"{{{ns}}}Value")
            v.text = str(act.avg_heart_rate)
        track.append(tp)
        end_ts = act.start_time + timedelta(seconds=act.duration_seconds)
        tp2 = ET.Element(f"{{{ns}}}Trackpoint")
        t2 = ET.SubElement(tp2, f"{{{ns}}}Time")
        t2.text = end_ts.strftime("%Y-%m-%dT%H:%M:%SZ")
        track.append(tp2)
    tree = ET.ElementTree(root)
    tree.write(filepath, encoding="UTF-8", xml_declaration=True)
    logger.info("Wrote TCX: %s", filepath)
    return filepath
