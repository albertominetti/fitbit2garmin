"""CLI entry point for garmin2fitbit conversion."""

import argparse
import logging
import os
import sys

from . import __version__
from .reader import read_all
from .writer import (
    write_activities_json,
    write_daily_summary_json,
    write_sleep_json,
    write_tcx_passthrough,
    write_weight_json,
)

logger = logging.getLogger(__name__)


def convert(
    input_dir: str,
    output_dir: str,
    activities: bool = True,
    tcx: bool = False,
    weight: bool = True,
    sleep: bool = True,
    summary: bool = True,
    verbose: bool = False,
) -> dict[str, list[str]]:
    """Convert Garmin data export to Fitbit-compatible formats.

    Args:
        input_dir: Directory with Garmin TCX files + CSV exports.
        output_dir: Where to write output files.
        activities: Write Fitbit JSON activities.
        tcx: Also write passthrough TCX files.
        weight: Write Fitbit JSON weight.
        sleep: Write Fitbit JSON sleep.
        summary: Write Fitbit daily field JSONs (steps, calories, distance).
        verbose: Enable debug logging.

    Returns:
        Dict of category -> list of output file paths.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    logger.info("Reading Garmin data from %s ...", input_dir)
    data = read_all(input_dir)

    os.makedirs(output_dir, exist_ok=True)
    results: dict[str, list[str]] = {}

    if activities and data.activities:
        path = write_activities_json(data, output_dir)
        if path:
            results["activities_json"] = [path]

    if tcx and data.activities:
        tcx_dir = os.path.join(output_dir, "activities")
        os.makedirs(tcx_dir, exist_ok=True)
        paths: list[str] = []
        for act in data.activities:
            p = write_tcx_passthrough(act, tcx_dir)
            if p:
                paths.append(p)
        if paths:
            results["activities_tcx"] = paths

    if weight and data.weight_logs:
        path = write_weight_json(data, output_dir)
        if path:
            results["weight"] = [path]

    if sleep and data.sleep_sessions:
        path = write_sleep_json(data, output_dir)
        if path:
            results["sleep"] = [path]

    if summary and data.daily_summaries:
        paths = write_daily_summary_json(data, output_dir)
        if paths:
            results["daily_summary"] = paths

    return results


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Convert Garmin data export to Fitbit-compatible formats",
    )
    p.add_argument(
        "input_dir",
        help="Directory with Garmin TCX files (in activities/) and CSV exports",
    )
    p.add_argument(
        "-o", "--output-dir",
        default="./fitbit_output",
        help="Output directory (default: ./fitbit_output)",
    )
    p.add_argument(
        "--no-activities", action="store_true",
        help="Skip Fitbit JSON activities output",
    )
    p.add_argument(
        "--tcx", action="store_true",
        help="Also generate TCX passthrough files (for Fitbit API upload)",
    )
    p.add_argument(
        "--no-weight", action="store_true",
        help="Skip body composition JSON export",
    )
    p.add_argument(
        "--no-sleep", action="store_true",
        help="Skip sleep JSON export",
    )
    p.add_argument(
        "--no-summary", action="store_true",
        help="Skip daily summary JSON export",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    p.add_argument(
        "--version", action="version",
        version=f"garmin2fitbit {__version__}",
    )
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
        tcx=args.tcx,
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
