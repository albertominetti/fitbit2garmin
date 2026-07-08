"""Write converted data to Garmin-compatible formats (TCX, CSV)."""

import csv
import logging
import os
import xml.etree.ElementTree as ET
from datetime import timedelta

from .models import Activity, DailySummary, FitbitData, SleepSession, WeightLog

logger = logging.getLogger(__name__)

TCX_NS = "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
ET.register_namespace("", TCX_NS)


def _make_tcx_trackpoint(timestamp_iso: str, bpm: int | None = None) -> ET.Element:
    tp = ET.Element(f"{{{TCX_NS}}}Trackpoint")
    t = ET.SubElement(tp, f"{{{TCX_NS}}}Time")
    t.text = timestamp_iso
    if bpm is not None:
        hr = ET.SubElement(tp, f"{{{TCX_NS}}}HeartRateBpm")
        v = ET.SubElement(hr, f"{{{TCX_NS}}}Value")
        v.text = str(bpm)
    return tp


def write_activity_tcx(activity: Activity, output_dir: str) -> str | None:
    """Write a single activity as a TCX file. Returns the output path or None."""
    if activity.duration_seconds <= 0:
        return None
    start_iso = activity.start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    filename = f"{activity.start_time.strftime('%Y%m%d_%H%M%S')}_{activity.sport}.tcx"
    filepath = os.path.join(output_dir, filename)
    root = ET.Element(f"{{{TCX_NS}}}TrainingCenterDatabase")
    activities = ET.SubElement(root, f"{{{TCX_NS}}}Activities")
    act_el = ET.SubElement(activities, f"{{{TCX_NS}}}Activity")
    act_el.set("Sport", activity.sport)
    act_id = ET.SubElement(act_el, f"{{{TCX_NS}}}Id")
    act_id.text = start_iso
    lap = ET.SubElement(act_el, f"{{{TCX_NS}}}Lap")
    lap.set("StartTime", start_iso)
    tt = ET.SubElement(lap, f"{{{TCX_NS}}}TotalTimeSeconds")
    tt.text = f"{activity.duration_seconds:.1f}"
    dist = ET.SubElement(lap, f"{{{TCX_NS}}}DistanceMeters")
    dist.text = f"{activity.distance_meters:.1f}"
    cal = ET.SubElement(lap, f"{{{TCX_NS}}}Calories")
    cal.text = str(activity.calories)
    intens = ET.SubElement(lap, f"{{{TCX_NS}}}Intensity")
    intens.text = "Active"
    trig = ET.SubElement(lap, f"{{{TCX_NS}}}TriggerMethod")
    trig.text = "Manual"
    if activity.avg_heart_rate:
        hr_av = ET.SubElement(lap, f"{{{TCX_NS}}}AverageHeartRateBpm")
        hav = ET.SubElement(hr_av, f"{{{TCX_NS}}}Value")
        hav.text = str(activity.avg_heart_rate)
    if activity.max_heart_rate:
        hr_mx = ET.SubElement(lap, f"{{{TCX_NS}}}MaximumHeartRateBpm")
        hmx = ET.SubElement(hr_mx, f"{{{TCX_NS}}}Value")
        hmx.text = str(activity.max_heart_rate)
    track = ET.SubElement(lap, f"{{{TCX_NS}}}Track")
    if activity.heart_rate_samples:
        for sample in activity.heart_rate_samples:
            ts = sample.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
            tp = _make_tcx_trackpoint(ts, sample.bpm)
            track.append(tp)
    else:
        tp = _make_tcx_trackpoint(start_iso, activity.avg_heart_rate)
        track.append(tp)
        end_ts = (activity.start_time + timedelta(seconds=activity.duration_seconds))
        tp2 = _make_tcx_trackpoint(
            end_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            None,
        )
        track.append(tp2)
    tree = ET.ElementTree(root)
    tree.write(filepath, encoding="UTF-8", xml_declaration=True)
    logger.info("Wrote TCX: %s", filepath)
    return filepath


def write_activities_to_tcx(data: FitbitData, output_dir: str) -> list[str]:
    """Write all activities to individual TCX files."""
    os.makedirs(output_dir, exist_ok=True)
    paths: list[str] = []
    for act in data.activities:
        path = write_activity_tcx(act, output_dir)
        if path:
            paths.append(path)
    return paths


def write_weight_csv(data: FitbitData, output_dir: str) -> str | None:
    """Write body composition CSV for Garmin Connect import.

    Garmin CSV format: Date,Weight,BMI,BodyFat,BoneMass,MuscleMass,BodyWater
    """
    if not data.weight_logs:
        return None
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, "body_composition.csv")
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Weight", "BMI", "BodyFat", "BoneMass", "MuscleMass", "BodyWater"])
        for log in data.weight_logs:
            date_str = log.date.strftime("%Y-%m-%d")
            w.writerow([
                date_str,
                f"{log.weight_kg:.2f}",
                f"{log.bmi:.1f}" if log.bmi else "",
                f"{log.body_fat_pct:.1f}" if log.body_fat_pct is not None else "",
                "", "",
            ])
    logger.info("Wrote body composition CSV: %s", filepath)
    return filepath


def write_sleep_csv(data: FitbitData, output_dir: str) -> str | None:
    """Write sleep data to CSV."""
    if not data.sleep_sessions:
        return None
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, "sleep.csv")
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "Date", "Start Time", "End Time", "Duration (min)",
            "Minutes Asleep", "Minutes Awake", "Efficiency",
            "Time in Bed (min)", "Minutes to Fall Asleep",
        ])
        for ses in data.sleep_sessions:
            w.writerow([
                ses.date.isoformat(),
                ses.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                ses.end_time.strftime("%Y-%m-%d %H:%M:%S"),
                ses.duration_millis // 60000,
                ses.minutes_asleep,
                ses.minutes_awake,
                ses.efficiency,
                ses.time_in_bed,
                ses.minutes_to_fall_asleep,
            ])
    logger.info("Wrote sleep CSV: %s", filepath)
    return filepath


def write_daily_summary_csv(data: FitbitData, output_dir: str) -> str | None:
    """Write daily summary (steps, calories, distance) to CSV."""
    if not data.daily_summaries:
        return None
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, "daily_summary.csv")
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Steps", "Calories", "Distance (m)"])
        for ds in data.daily_summaries:
            w.writerow([
                ds.date.isoformat(),
                ds.steps,
                f"{ds.calories:.1f}",
                f"{ds.distance_meters:.1f}",
            ])
    logger.info("Wrote daily summary CSV: %s", filepath)
    return filepath
