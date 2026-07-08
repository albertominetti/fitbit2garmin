# fitbit2garmin

Convert your Fitbit data export to Garmin-compatible formats for import into Garmin Connect.

After years using Fitbit for activity tracking, heart rate monitoring, sleep analysis, and weight logging, migrating to Garmin means leaving your history behind — unless you bring it with you. This tool translates your Fitbit Google Takeout export into files that Garmin Connect can actually import.

---

## Table of Contents

- [Exporting Your Fitbit Data](#exporting-your-fitbit-data)
- [Fitbit Input Formats](#fitbit-input-formats)
- [Garmin Output Formats](#garmin-output-formats)
- [Feature Comparison: Fitbit vs Garmin](#feature-comparison-fitbit-vs-garmin)
- [Conversion Mapping](#conversion-mapping)
- [How the Integration Works](#how-the-integration-works)
- [Installation](#installation)
- [Usage](#usage)
- [Importing into Garmin Connect](#importing-into-garmin-connect)
- [Sample Data](#sample-data)
- [File Format Specifications](#file-format-specifications)
- [Limitations](#limitations)
- [FAQ](#faq)

---

## Exporting Your Fitbit Data

Since Google's acquisition of Fitbit, all data exports go through **Google Takeout**.

### Step-by-step

1. Go to [Google Takeout](https://takeout.google.com/)
2. Click **Deselect all**, then search for and select **Fitbit**
3. Choose **JSON** format (recommended — CSV also works for some types)
4. Set delivery to email, frequency to single export, and file size to 2 GB
5. Click **Create export**
6. Wait for the email (minutes to hours depending on data volume)
7. Download and extract the ZIP archive

### Directory structure

The extracted archive follows this layout:

```
Takeout/
├── Fitbit/
│   ├── Global Export Data/           ← daily summaries + sensors
│   │   ├── heart_rate-2024-01-15.json
│   │   ├── sleep-2024-01-15.json
│   │   ├── activities-2024-01-15.json
│   │   ├── steps-2024-01-15.json
│   │   ├── calories-2024-01-15.json
│   │   ├── distance-2024-01-15.json
│   │   └── weight-2024-01-15.json
│   ├── Physical Activity/            ← detailed workout records
│   │   └── activities-2024-01-15.json
│   ├── Body/                         ← weight & body composition
│   │   └── weight-2024-01-15.json
│   └── Personal & Account/           ← profile, devices, settings
└── ...
```

Point the converter at the `Takeout/Fitbit/` or any directory containing these JSON files.

---

## Fitbit Input Formats

The converter reads all common Fitbit JSON structures found in Google Takeout. Below are the actual formats with real sample data.

### Heart Rate (`heart_rate-*.json`)

Two formats are supported:

**Intraday samples (most common in Takeout):**
```json
[
  {"dateTime": "01/15/24 07:30:00", "value": {"bpm": 95, "confidence": 3}},
  {"dateTime": "01/15/24 07:35:00", "value": {"bpm": 112, "confidence": 3}}
]
```

**Daily summary with zones (older format):**
```json
{
  "activities-heart": [
    {
      "dateTime": "2024-01-15",
      "value": {
        "restingHeartRate": 62,
        "heartRateZones": [
          {"name": "Out of Range", "min": 30, "max": 90, "minutes": 180},
          {"name": "Fat Burn", "min": 91, "max": 140, "minutes": 60}
        ]
      }
    }
  ]
}
```

Date formats accepted: `MM/dd/yy HH:mm:ss`, `YYYY-MM-dd HH:mm:ss`, `YYYY-MM-ddTHH:mm:ss`, `MM/dd/YYYY HH:mm:ss`.

### Sleep (`sleep-*.json`)

```json
{
  "sleep": [
    {
      "dateOfSleep": "2024-01-15",
      "duration": 29400000,
      "efficiency": 93,
      "startTime": "2024-01-14T23:15:00.000",
      "endTime": "2024-01-15T07:20:00.000",
      "minutesAsleep": 445,
      "minutesAwake": 25,
      "minutesToFallAsleep": 12,
      "timeInBed": 485,
      "isMainSleep": true,
      "type": "stages",
      "levels": {
        "data": [
          {"dateTime": "2024-01-14T23:15:00.000", "level": "light", "seconds": 2400},
          {"dateTime": "2024-01-14T23:55:00.000", "level": "deep", "seconds": 3300}
        ],
        "summary": {
          "deep": {"count": 2, "minutes": 95},
          "light": {"count": 5, "minutes": 245},
          "rem": {"count": 3, "minutes": 90},
          "wake": {"count": 3, "minutes": 25},
          "asleep": {"count": 1, "minutes": 430}
        }
      }
    }
  ]
}
```

Both `"type": "stages"` (with REM/deep/light) and `"type": "classic"` (restless/asleep/awake) are supported. The converter correctly handles the summary object where `"asleep"` is the total and `"deep"`, `"light"`, `"rem"` are breakdowns — no double-counting.

**Classic sleep example (older devices):**
```json
{
  "sleep": [
    {
      "dateOfSleep": "2024-06-10",
      "duration": 28200000,
      "efficiency": 87,
      "startTime": "2024-06-09T23:45:00.000",
      "endTime": "2024-06-10T07:30:00.000",
      "minutesAsleep": 430,
      "minutesAwake": 40,
      "minutesToFallAsleep": 18,
      "timeInBed": 470,
      "isMainSleep": true,
      "type": "classic",
      "levels": {
        "data": [
          {"dateTime": "2024-06-09T23:45:00.000", "level": "restless", "seconds": 600},
          {"dateTime": "2024-06-10T00:00:00.000", "level": "asleep", "seconds": 3600},
          {"dateTime": "2024-06-10T01:00:00.000", "level": "restless", "seconds": 300},
          {"dateTime": "2024-06-10T01:05:00.000", "level": "asleep", "seconds": 7200},
          {"dateTime": "2024-06-10T03:05:00.000", "level": "awake", "seconds": 120},
          {"dateTime": "2024-06-10T03:07:00.000", "level": "asleep", "seconds": 10800},
          {"dateTime": "2024-06-10T06:07:00.000", "level": "restless", "seconds": 480},
          {"dateTime": "2024-06-10T06:15:00.000", "level": "awake", "seconds": 900}
        ],
        "shortData": [],
        "summary": {
          "restless": {"count": 3, "minutes": 23},
          "awake": {"count": 2, "minutes": 17},
          "asleep": {"count": 3, "minutes": 430}
        }
      }
    }
  ]
}
```

### Activities: Daily Summary (`activities-*.json` in Global Export Data)

```json
{
  "activities": [
    {
      "activityName": "Morning Run",
      "activityTypeId": 90009,
      "activeDuration": 2700000,
      "originalDuration": 2750000,
      "calories": 380,
      "steps": 7200,
      "distance": 8500,
      "distanceUnit": "METERS",
      "startTime": "2024-01-15T07:30:00.000",
      "heartRateZones": [
        {"name": "Out of Range", "min": 30, "max": 90, "minutes": 8},
        {"name": "Fat Burn", "min": 91, "max": 140, "minutes": 22},
        {"name": "Cardio", "min": 141, "max": 170, "minutes": 14},
        {"name": "Peak", "min": 171, "max": 220, "minutes": 1}
      ]
    }
  ]
}
```

### Activities: Detailed Workout (`Physical Activity/`)

The same format as above but stored in a separate folder by Google Takeout. These often contain more detail including GPS data (though GPS trackpoints are not yet extracted — see limitations).

### Steps, Calories, Distance (`steps-*.json`, `calories-*.json`, `distance-*.json`)

```json
[
  {"dateTime": "2024-01-15", "value": "12400"}
]
```

These are daily totals. The `value` field is a string that is parsed as a float. Distance units depend on user locale settings (kilometers or miles).

### Weight / Body Composition (`weight-*.json`)

```json
[
  {"dateTime": "2024-01-15", "value": {"weight": 75.5, "bmi": 23.5, "fat": 18.0}}
]
```

Timestamps can be date-only (`"2024-01-15"`) or datetime (`"2024-01-20T08:00:00"`). Both `Body/` and `Global Export Data/` locations are scanned.

---

## Garmin Output Formats

### TCX (Training Center XML)

Garmin's native XML format for activities. Supports sport type, duration, distance, calories, lap data, and per-trackpoint heart rate.

```xml
<?xml version='1.0' encoding='UTF-8'?>
<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">
  <Activities>
    <Activity Sport="Running">
      <Id>2024-01-15T07:30:00Z</Id>
      <Lap StartTime="2024-01-15T07:30:00Z">
        <TotalTimeSeconds>2750.0</TotalTimeSeconds>
        <DistanceMeters>8500.0</DistanceMeters>
        <Calories>380</Calories>
        <Intensity>Active</Intensity>
        <TriggerMethod>Manual</TriggerMethod>
        <AverageHeartRateBpm><Value>126</Value></AverageHeartRateBpm>
        <MaximumHeartRateBpm><Value>155</Value></MaximumHeartRateBpm>
        <Track>
          <Trackpoint>
            <Time>2024-01-15T07:30:00Z</Time>
            <HeartRateBpm><Value>95</Value></HeartRateBpm>
          </Trackpoint>
        </Track>
      </Lap>
    </Activity>
  </Activities>
</TrainingCenterDatabase>
```

**Sport types emitted:** Running, Walking, Hiking, Treadmill, Biking, Stationary Biking, Swimming, Elliptical, Strength, Yoga, Golf, Tennis, CrossFit, HIIT, Other, and more. Maps directly from Fitbit's `activityTypeId`.

### CSV: Body Composition

Formatted for Garmin Connect's body composition import tool:

```
Date,Weight,BMI,BodyFat,BoneMass,MuscleMass,BodyWater
2024-01-15,75.50,23.5,18.0,,
2024-01-16,75.80,23.6,18.2,,
```

Garmin Connect maps these columns as:
- **Date** → date of measurement
- **Weight** → body weight in kg
- **BMI** → body mass index (auto-calculated by Garmin if empty)
- **BodyFat** → body fat percentage
- **BoneMass, MuscleMass, BodyWater** → left empty (not available from Fitbit export)

### CSV: Sleep

Reference CSV for your records. Garmin Connect does not support sleep data import:

```
Date,Start Time,End Time,Duration (min),Minutes Asleep,Minutes Awake,Efficiency,Time in Bed (min),Minutes to Fall Asleep
2024-01-15,2024-01-14 23:15:00,2024-01-15 07:20:00,490,430,25,93,485,12
```

### CSV: Daily Summary

Daily totals for steps, calories, and distance:

```
Date,Steps,Calories,Distance (m)
2024-01-15,12400,2520.0,14.3
```

> **Note:** Distance units in Fitbit's `distance-*.json` files are locale-dependent (km for metric, miles for imperial). The converter passes the raw value through. Adjust units in the CSV if needed.

---

## Feature Comparison: Fitbit vs Garmin

| Feature | Fitbit | Garmin | Conversion |
|---|---|---|---|
| **Running/Walking/Cycling** | activityName + typeId + zones | Sport type + HR zones | → TCX activity |
| **Heart rate (intraday)** | `{bpm, confidence}` per sample | Per-trackpoint in TCX/FIT | → TCX trackpoints |
| **Heart rate (daily)** | Resting HR + zone minutes | Resting HR + intensity mins | → In TCX lap summary |
| **Sleep stages** | REM / Deep / Light / Awake | REM / Deep / Light / Awake | → CSV only (no Garmin import) |
| **Sleep score** | Efficiency % | Sleep score (1-100) | Not mapped |
| **Weight & BMI** | Manual or scale logs | Manual or scale logs | → CSV import |
| **Body fat %** | With Aria scale | With Index scale | → CSV import |
| **Steps** | Daily total | Daily total | → CSV only |
| **Calories** | Active + BMR combined | Active + Resting split | → CSV only |
| **Distance** | Daily total | Daily total (GPS-based) | → CSV only |
| **GPS tracks** | Per workout | Per activity .FIT/.GPX | Partial (see limitations) |
| **VO2 Max** | Cardio Fitness Score | VO2 Max estimate | Not available |
| **Floors climbed** | Barometric | Barometric (most devices) | Not converted |
| **Food / Nutrition** | Barcode scanning | Manual (Connect) | Not converted |
| **Water intake** | Manual log | Manual log | Not converted |
| **Menstrual health** | Cycle tracking | Cycle tracking | Not converted |
| **SpO2 / Blood oxygen** | Nightly average | Pulse Ox | Not converted |
| **Stress / HRV** | Stress score | Stress + Body Battery | Not converted |

---

## Conversion Mapping

### Fitbit Activity Type → Garmin Sport

| Fitbit activityTypeId | Fitbit activityName (example) | Garmin Sport |
|---|---|---|
| 90009 | Run, Morning Run | **Running** |
| 90010 | Walk, Evening Walk | **Walking** |
| 90011 | Hike | **Hiking** |
| 90012 | Treadmill | **Running** (indoor) |
| 90013 | Cycling, Bike | **Biking** |
| 90014 | Stationary Bike, Spinning | **Stationary Biking** |
| 90015 | Swim, Swimming | **Swimming** |
| 90016 | Elliptical | **Elliptical** |
| 90017 | Weights, Strength | **Strength** |
| 90018 | Yoga | **Yoga** |
| 90019 | Tennis | **Tennis** |
| 90020 | Basketball | **Basketball** |
| 90022 | Golf | **Golfing** |
| 90027 | Meditation | **Other** |
| 90028 | Cardio | **Other** |
| 90033 | HIIT | **Other** |
| *unknown* | Run | Running |
| *unknown* | Walk | Walking |
| *unknown* | Swim | Swimming |

When `activityTypeId` is not present, the converter falls back to keyword matching on the activity name.

### Activity Duration

- Fitbit stores durations in **milliseconds** (both `activeDuration` and `originalDuration`)
- The converter uses the larger of the two, divided by 1000 to get **seconds**
- Garmin TCX stores duration as `<TotalTimeSeconds>` (decimal seconds)

### Heart Rate

- **Per-trackpoint**: Intraday HR samples from `heart_rate-*.json` files that overlap with the activity time window are matched and added as `<Trackpoint><HeartRateBpm>` elements in the TCX
- **Average HR**: Calculated from matched trackpoint BPM values, or taken from the activity's `heartRate` object if present
- **Max HR**: Derived from matched samples (actual peak), not zone boundaries
- **Matching window**: 30 seconds before activity start to 30 seconds after activity end

### Distance & Calories

- **Distance**: Passed through in meters. Both the `activities-*.json` (with `distanceUnit: "METERS"`) and `distance-*.json` are read
- **Calories**: Passed through directly as integer from the activity record

---

## How the Integration Works

### Architecture

```
┌─────────────────────┐
│  Google Takeout ZIP │
└────────┬────────────┘
         │ unzip
         ▼
┌─────────────────────┐
│  Takeout/Fitbit/    │
│  ├─ Global Export   │
│  ├─ Physical Act.   │
│  └─ Body            │
└────────┬────────────┘
         │ python -m fitbit2garmin
         ▼
┌─────────────────────────────────────────┐
│  fitbit2garmin (reader + converter)     │
│                                         │
│  1. Scan directory for *.json files     │
│     grouped by type (heart_rate,        │
│     sleep, activities, steps, etc.)     │
│                                         │
│  2. Parse each JSON file                │
│     Handle date formats, field names,   │
│     and structural variations across     │
│     different Takeout versions          │
│                                         │
│  3. Cross-reference data                │
│     Match HR samples to activities by   │
│     time range overlap                  │
│                                         │
│  4. Generate output files               │
│     TCX for activities (with embedded   │
│     HR trackpoints)                     │
│     CSV for body, sleep, daily summary  │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────┐
│  garmin_output/     │
│  ├─ activities/     │ ← TCX files (import to Garmin Connect)
│  │  ├─ 20240115_*  │
│  │  ├─ 20240116_*  │
│  │  └─ ...         │
│  ├─ body_composition.csv  │ ← Import: Health Stats → Body Comp
│  ├─ sleep.csv             │ ← Reference only
│  └─ daily_summary.csv     │ ← Reference only
└─────────────────────┘
```

### Data Flow

1. **Reader** (`reader.py`): Walks the input directory tree, identifies JSON files by filename prefix (`heart_rate-`, `sleep-`, `activities-`, `steps-`, `calories-`, `distance-`, `weight-`, `body-`), and parses each into the internal data models (`Activity`, `HeartRateSample`, `SleepSession`, `WeightLog`, `DailySummary`).

2. **Converter** (`converter.py`): Takes the raw parsed data and cross-references it. The key transformation is matching global HR samples to activities. It also optionally builds synthetic "Other" activities for days that have HR data but no recorded workout (the `--hr-only` flag).

3. **Writer** (`writer.py`): Serializes the processed data into Garmin-compatible formats using XML (`xml.etree.ElementTree`) for TCX and the `csv` module for CSV files.

### HR Matching Algorithm

```
For each activity:
  1. Calculate time window: [start - 30s, end + 30s]
  2. Find all HeartRateSamples within that window
  3. If samples found:
     - Attach them as Trackpoints (in chronological order)
     - Compute average HR from sample BPM values
     - Compute max HR as the peak BPM value
     - Override any zone-based estimates with actual data

For each day with HR samples but no activity (--hr-only):
  1. Collect all samples for that date
  2. If >= 10 samples exist and span >= 60 seconds:
     - Create a synthetic "Other" activity
     - Duration = span of samples
     - All samples become trackpoints
     - avg/max HR from sample data
```

---

## Installation

```bash
# No installation required — run directly:
python -m fitbit2garmin /path/to/Takeout/Fitbit -o ./output

# Or install with pip for use as a command:
pip install -e /path/to/fitbit2garmin
fitbit2garmin /path/to/Takeout/Fitbit -o ./output
```

Requires Python 3.10+. No external dependencies — uses only the standard library.

---

## Usage

```
usage: python -m fitbit2garmin [-h] [-o OUTPUT_DIR] [--no-activities]
                                [--hr-only] [--no-weight] [--no-sleep]
                                [--no-summary] [-v] [--version]
                                input_dir

Convert Fitbit data export to Garmin-compatible formats

positional arguments:
  input_dir             Path to Fitbit export directory (extracted
                        Takeout/Fitbit or similar)

options:
  -h, --help            show this help message and exit
  -o, --output-dir OUTPUT_DIR
                        Output directory (default: ./garmin_output)
  --no-activities       Skip activity-to-TCX conversion
  --hr-only             Create TCX files for days with HR data even without a
                        recorded activity
  --no-weight           Skip body composition CSV export
  --no-sleep            Skip sleep CSV export
  --no-summary          Skip daily summary CSV export
  -v, --verbose         Verbose output
  --version             show program's version number and exit
```

### Examples

```bash
# Basic conversion (all categories)
python -m fitbit2garmin ~/Downloads/Takeout/Fitbit -o ./garmin_data

# Activities + weight only, verbose logging
python -m fitbit2garmin ~/Downloads/Takeout/Fitbit -o ./garmin_data \
  --no-sleep --no-summary -v

# Generate TCX for all days with heart rate data (even non-activity days)
python -m fitbit2garmin ~/Downloads/Takeout/Fitbit -o ./garmin_data --hr-only

# TCX files only, no CSVs
python -m fitbit2garmin ~/Downloads/Takeout/Fitbit -o ./garmin_data \
  --no-weight --no-sleep --no-summary
```

---

## Importing into Garmin Connect

### Activities (TCX files)

1. Go to [Garmin Connect](https://connect.garmin.com/) and sign in
2. Click **Activities** in the top navigation bar
3. Click **Import Data** (top-right, gear icon dropdown)
4. Select **Import from file...**
5. Choose one or more `.tcx` files from `output/activities/`
6. Click **Upload**

Repeat for each activity (Garmin does not support batch upload). Each uploaded activity will appear in your history with duration, distance, calories, heart rate data, and sport type.

### Body Composition (CSV)

1. In Garmin Connect, go to **Health Stats** (in the main menu)
2. Go to **Body Composition**
3. Click the gear icon → **Import Data**
4. Select the `body_composition.csv` file
5. Map columns:
   - **Date** → Date
   - **Weight** → Weight (kg)
   - **Body Fat** → Body Fat %
   - **BMI** → BMI
6. Click **Import**

Garmin will show these measurements alongside your Garmin-device readings.

### Sleep and Daily Summary (CSV)

Garmin Connect **does not** support importing sleep or daily step/calorie/distance data via CSV. These files are provided for your personal records and can be opened in any spreadsheet application (Excel, Google Sheets, Numbers).

---

## Sample Data

The `sample/` directory contains representative Fitbit export data and the corresponding converter output:

```
sample/
├── input/
│   ├── Global Export Data/
│   │   ├── heart_rate-2024-01-15.json    # Intraday HR (16 samples)
│   │   ├── sleep-2024-01-15.json          # Sleep with stages + levels data
│   │   ├── sleep-2024-01-16.json          # Second night (summary only, no levels data)
│   │   ├── activities-2024-01-15.json     # 2 activities: Run + Walk
│   │   ├── activities-2024-01-16.json     # 1 activity: Cycling
│   │   ├── weight-2024-01-15.json         # Body weight x 3 days
│   │   ├── steps-2024-01-15.json          # Daily steps
│   │   ├── steps-2024-01-16.json
│   │   ├── calories-2024-01-15.json       # Daily calories
│   │   ├── calories-2024-01-16.json
│   │   ├── distance-2024-01-15.json       # Daily distance
│   │   └── distance-2024-01-16.json
│   ├── Physical Activity/
│   │   └── heart_rate-2024-01-16.json     # Cycling HR samples (ISO dates)
│   └── Body/
│       └── weight-2024-01-20.json         # Weight with timestamp
│
└── output/
    ├── activities/
    │   ├── 20240115_073000_Running.tcx     # Morning Run with HR trackpoints
    │   ├── 20240115_183000_Walking.tcx     # Evening Walk with HR trackpoints
    │   └── 20240116_090000_Cycling.tcx     # Cycling with 12 HR trackpoints
    ├── body_composition.csv                # 4 weight entries
    ├── sleep.csv                           # 2 sleep sessions
    └── daily_summary.csv                   # 2 days of summaries
```

To regenerate the sample output:

```bash
python -m fitbit2garmin sample/input -o sample/output --hr-only
```

### What the sample demonstrates

| Scenario | Sample file | What it tests |
|---|---|---|
| **Intraday HR** | `heart_rate-2024-01-15.json` | M/dd/yy date format, confidence levels, HR matched to activities |
| **ISO date HR** | `Physical Activity/heart_rate-2024-01-16.json` | ISO date format, HR matched to Cycling activity |
| **Sleep with stages** | `sleep-2024-01-15.json` | Full levels.data array, summary with "asleep" total |
| **Sleep summary-only** | `sleep-2024-01-16.json` | Summary object without levels.data |
| **Multiple activities** | `activities-2024-01-15.json` | Two activities (Run + Walk) on same day |
| **Cycling activity** | `activities-2024-01-16.json` | Biking sport type, longer duration |
| **Weight from Global Export** | `weight-2024-01-15.json` | Date-only timestamps, multiple entries |
| **Weight from Body folder** | `Body/weight-2024-01-20.json` | Datetime timestamps in Body/ subfolder |
| **Steps + calories + distance** | `*-2024-01-{15,16}.json` | Daily summary aggregation |

---

## File Format Specifications

### TCX Schema (simplified)

```xml
TrainingCenterDatabase
└── Activities
    └── Activity (@Sport)
        ├── Id                          (ISO 8601 timestamp)
        └── Lap (@StartTime)
            ├── TotalTimeSeconds        (decimal seconds)
            ├── DistanceMeters          (decimal meters)
            ├── Calories                (integer kcal)
            ├── Intensity               ("Active" | "Resting")
            ├── TriggerMethod           ("Manual" | "Auto")
            ├── AverageHeartRateBpm
            │   └── Value
            ├── MaximumHeartRateBpm
            │   └── Value
            └── Track
                └── Trackpoint (repeating)
                    ├── Time            (ISO 8601)
                    └── HeartRateBpm
                        └── Value
```

Filename convention: `YYYYMMDD_HHMMSS_Sport.tcx`

### Body Composition CSV

```
Date,Weight,BMI,BodyFat,BoneMass,MuscleMass,BodyWater
```

- Date: `YYYY-MM-DD`
- Weight: kg (decimal)
- BMI: decimal
- BodyFat: percentage (decimal)
- BoneMass / MuscleMass / BodyWater: left empty (data not available from Fitbit)

---

## Limitations

| Limitation | Details |
|---|---|
| **No GPS trackpoints** | Fitbit's `activities-*.json` exports do not include GPS coordinates or route data. TCX files contain time + heart rate only, not lat/lon |
| **No sleep import** | Garmin Connect does not expose a sleep data import API. Sleep CSVs are for personal reference only |
| **No batch upload to Garmin** | Garmin Connect's web UI requires selecting TCX files one-by-one |
| **Distance units ambiguous** | Daily summary distance from `distance-*.json` has no unit field. Value is passed as-is (km for metric users, miles for imperial) |
| **No SpO2 / HRV / Stress** | These sensor data types from Fitbit are not covered by this converter |
| **No food / nutrition** | Fitbit food logs are not converted |
| **No floors** | Fitbit floor data (`floors-*.json`) is not currently processed |
| **Heart rate confidence** | Fitbit's `confidence` field (0-3) is parsed but not used in TCX output |

---

## FAQ

### Does this work with Google Health (the renamed Fitbit app)?

Yes. Google Takeout still labels the data category as "Fitbit" even after the rebrand. The folder structure and JSON formats are unchanged.

### Can I import TCX files on mobile?

Garmin Connect Mobile does not support TCX import. Use the web version at connect.garmin.com on a desktop browser.

### My activity durations look wrong — what's activeDuration vs originalDuration?

Fitbit records two durations:
- `activeDuration`: time spent actually moving (excluding pauses, rests)
- `originalDuration`: total elapsed time including pauses

The converter uses the **larger** of the two values, which typically gives the total time (most appropriate for Garmin's activity representation).

### Can I run this on my Pixel Watch data?

Yes. Pixel Watch data is stored in the same Fitbit/Google Health infrastructure and exports via Google Takeout with the same JSON format.

### What about the July 2026 data deletion?

If you never migrated your legacy Fitbit account to a Google account, Google will start permanently deleting un-migrated data on **15 July 2026**. Export your data via Takeout before then. Already-migrated accounts are not affected.

### Why don't I see HR data in my imported activities?

The converter matches heart rate samples to activities by time overlap. If your HR files use a different date format than expected, or if the timestamps don't align with the activity time window, HR may not be embedded. Run with `-v` to see how many HR samples were found and matched.

---

## Project Structure

```
fitbit2garmin/
├── README.md
├── setup.py
├── sample/
│   ├── input/            ← Sample Fitbit export (use as reference)
│   └── output/           ← Generated Garmin-compatible files
└── fitbit2garmin/
    ├── __init__.py       ← Package metadata
    ├── __main__.py       ← `python -m` entry point
    ├── models.py         ← Data classes (Activity, SleepSession, etc.)
    ├── reader.py         ← Fitbit JSON parser (handles all date formats)
    ├── writer.py         ← TCX/CSV output generator
    └── converter.py      ← CLI + conversion orchestration + HR matching
```
