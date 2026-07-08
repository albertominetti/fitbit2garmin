"""Conversion orchestration and CLI."""

import argparse
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta

from . import __version__
from .models import Activity, FitbitData, HeartRateSample
from .reader import read_all
from .writer import (
    write_activity_tcx,
    write_daily_summary_csv,
    write_sleep_csv,
    write_weight_csv,
)

AVG_WALK_CADENCE = 100
STRIDE_LENGTH_M = 0.75

logger = logging.getLogger(__name__)


def _match_hr_to_activities(data: FitbitData, padding_seconds: int = 30):
    """Match global heart rate samples to activities based on time overlap."""
    if not data.heart_rate_samples or not data.activities:
        return
    for act in data.activities:
        act_end = act.start_time + timedelta(seconds=act.duration_seconds)
        matched = [
            s for s in data.heart_rate_samples
            if act.start_time - timedelta(seconds=padding_seconds)
            <= s.timestamp
            <= act_end + timedelta(seconds=padding_seconds)
        ]
        if matched:
            act.heart_rate_samples = sorted(matched, key=lambda s: s.timestamp)
            bpm_vals = [s.bpm for s in matched if s.bpm > 0]
            if bpm_vals:
                act.avg_heart_rate = round(sum(bpm_vals) / len(bpm_vals))
                act.max_heart_rate = max(bpm_vals)


def _build_hr_only_activities(data: FitbitData, min_samples: int = 10) -> list[Activity]:
    """Create synthetic 'Other' activities for days with HR data but no activities."""
    if not data.heart_rate_samples:
        return []
    hr_by_date: dict[datetime.date, list[HeartRateSample]] = defaultdict(list)
    for s in data.heart_rate_samples:
        hr_by_date[s.timestamp.date()].append(s)

    activity_dates: set[datetime.date] = set()
    for act in data.activities:
        activity_dates.add(act.start_time.date())
        activity_dates.add((act.start_time + timedelta(seconds=act.duration_seconds)).date())

    extras: list[Activity] = []
    for date_key, samples in sorted(hr_by_date.items()):
        if date_key in activity_dates:
            continue
        if len(samples) < min_samples:
            continue
        samples.sort(key=lambda s: s.timestamp)
        bpm_vals = [s.bpm for s in samples if s.bpm > 0]
        if not bpm_vals:
            continue
        duration = (samples[-1].timestamp - samples[0].timestamp).total_seconds()
        if duration < 60:
            continue
        act = Activity(
            name=f"Heart Rate {date_key.isoformat()}",
            sport="Other",
            start_time=samples[0].timestamp,
            duration_seconds=duration,
            heart_rate_samples=samples,
            avg_heart_rate=round(sum(bpm_vals) / len(bpm_vals)),
            max_heart_rate=max(bpm_vals),
        )
        extras.append(act)
    return extras


def _build_daily_activities(data: FitbitData) -> list[Activity]:
    """Create Walking TCX activities from daily step/calorie/distance summaries."""
    if not data.daily_summaries:
        return []
    existing_keys: set[tuple] = set()
    for act in data.activities:
        d = act.start_time.date()
        existing_keys.add((d, act.sport))

    extras: list[Activity] = []
    for ds in data.daily_summaries:
        if ds.steps <= 0:
            continue
        key = (ds.date, "Walking")
        if key in existing_keys:
            continue
        existing_keys.add(key)
        duration_min = ds.steps / AVG_WALK_CADENCE
        duration_s = int(duration_min * 60)
        if duration_s < 60:
            continue
        dist = ds.steps * STRIDE_LENGTH_M
        start = datetime(ds.date.year, ds.date.month, ds.date.day, 12, 0, 0)
        sample_interval = max(60, duration_s // 10)
        samples: list[HeartRateSample] = []
        for i in range(11):
            t = start + timedelta(seconds=i * sample_interval)
            if t > start + timedelta(seconds=duration_s):
                t = start + timedelta(seconds=duration_s)
            samples.append(HeartRateSample(t, 0, 0))
        act = Activity(
            name=f"Daily {ds.date.isoformat()}",
            sport="Walking",
            start_time=start,
            duration_seconds=duration_s,
            calories=int(ds.calories),
            distance_meters=dist,
            steps=ds.steps,
            heart_rate_samples=samples,
        )
        extras.append(act)
    return extras


def convert(
    input_dir: str,
    output_dir: str,
    activities: bool = True,
    hr_only: bool = False,
    weight: bool = True,
    sleep: bool = True,
    summary: bool = True,
    verbose: bool = False,
) -> dict[str, list[str]]:
    """Convert Fitbit export data to Garmin-compatible formats.

    Returns a dict of category -> list of output file paths.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    logger.info("Reading Fitbit data from %s ...", input_dir)
    data: FitbitData = read_all(input_dir)
    logger.info(
        "Found: %d activities, %d HR samples, %d sleep sessions, "
        "%d weight logs, %d daily summaries",
        len(data.activities),
        len(data.heart_rate_samples),
        len(data.sleep_sessions),
        len(data.weight_logs),
        len(data.daily_summaries),
    )

    os.makedirs(output_dir, exist_ok=True)
    results: dict[str, list[str]] = {}

    _match_hr_to_activities(data)

    tcx_activities = list(data.activities)

    if data.daily_summaries:
        daily_acts = _build_daily_activities(data)
        tcx_activities.extend(daily_acts)
        logger.info("Added %d daily summary activities (steps/calories/distance)", len(daily_acts))

    if hr_only:
        extras = _build_hr_only_activities(data)
        tcx_activities.extend(extras)
        logger.info("Added %d HR-only activities", len(extras))

    if activities and tcx_activities:
        tcx_dir = os.path.join(output_dir, "activities")
        os.makedirs(tcx_dir, exist_ok=True)
        paths: list[str] = []
        for act in tcx_activities:
            path = write_activity_tcx(act, tcx_dir)
            if path:
                paths.append(path)
        results["activities"] = paths
        logger.info("Wrote %d activity TCX files to %s", len(paths), tcx_dir)

    if weight and data.weight_logs:
        path = write_weight_csv(data, output_dir)
        if path:
            results["weight"] = [path]

    if sleep and data.sleep_sessions:
        path = write_sleep_csv(data, output_dir)
        if path:
            results["sleep"] = [path]

    if summary and data.daily_summaries:
        path = write_daily_summary_csv(data, output_dir)
        if path:
            results["daily_summary"] = [path]

    return results


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Convert Fitbit data export to Garmin-compatible formats",
    )
    p.add_argument(
        "input_dir",
        help="Path to Fitbit export directory (extracted Takeout/Fitbit or similar)",
    )
    p.add_argument(
        "-o", "--output-dir",
        default="./garmin_output",
        help="Output directory (default: ./garmin_output)",
    )
    p.add_argument(
        "--no-activities", action="store_true",
        help="Skip activity-to-TCX conversion",
    )
    p.add_argument(
        "--hr-only", action="store_true",
        help="Create TCX files for days with HR data even without a recorded activity",
    )
    p.add_argument(
        "--no-weight", action="store_true",
        help="Skip body composition CSV export",
    )
    p.add_argument(
        "--no-sleep", action="store_true",
        help="Skip sleep CSV export",
    )
    p.add_argument(
        "--no-summary", action="store_true",
        help="Skip daily summary CSV export",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    p.add_argument("--version", action="version", version=f"fitbit2garmin {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not os.path.isdir(args.input_dir):
        logger.error("Input directory does not exist: %s", args.input_dir)
        print(f"Error: input directory not found: {args.input_dir}", file=sys.stderr)
        return 1

    results = convert(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        activities=not args.no_activities,
        hr_only=args.hr_only,
        weight=not args.no_weight,
        sleep=not args.no_sleep,
        summary=not args.no_summary,
        verbose=args.verbose,
    )

    total = sum(len(v) for v in results.values())
    print(f"\nDone! Wrote {total} files to {args.output_dir}/")
    for category, paths in results.items():
        print(f"  {category}: {len(paths)} file(s)")
        for p in paths[:3]:
            print(f"    - {p}")
        if len(paths) > 3:
            print(f"    ... and {len(paths) - 3} more")

    return 0
