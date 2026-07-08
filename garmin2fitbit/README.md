# garmin2fitbit

Convert Garmin data exports into Fitbit-compatible JSON format for archival or API-based migration.

Fitbit has **no official bulk import feature**. Unlike Garmin Connect (which accepts TCX and CSV), the only way to get historical data into Fitbit is through the **Fitbit Web API** or **third-party sync apps** (RunGap, HealthSync) that use it. This converter prepares your Garmin data in the right format.

---

## Table of Contents

- [Feature & Import Feasibility](#feature--import-feasibility)
- [Garmin Input Formats](#garmin-input-formats)
- [Fitbit Output Formats](#fitbit-output-formats)
- [Installation](#installation)
- [Usage](#usage)
- [Third-Party Import Options](#third-party-import-options)
- [Setting Up Garmin Export](#setting-up-garmin-export)
- [Limitations](#limitations)

---

## Feature & Import Feasibility

| Garmin Data | Fitbit Output | Import into Fitbit | Path |
|---|---|---|---|---|
| **Activities** (TCX: running, walking, cycling, etc.) | `activities.json` + TCX passthrough | ⚠️ Possible | RunGap, HealthSync, or direct Fitbit API [`POST /1/user/-/activities.json`](https://dev.fitbit.com/build/reference/web-api/activity/create-activity/) |
| **Heart rate** (per-trackpoint from TCX) | Embedded in `activities.json` + zones | ❌ | No API endpoint to upload HR data; only third-party tools that accept TCX can carry it |
| **Weight & BMI** (CSV) | `weight.json` | ⚠️ Possible | Fitbit API [`POST /1/user/-/body/log/weight.json`](https://dev.fitbit.com/build/reference/web-api/body/log-weight/) |
| **Body fat %** (CSV) | `weight.json` (with `fat` field) | ⚠️ Possible | Fitbit API [`POST /1/user/-/body/log/fat.json`](https://dev.fitbit.com/build/reference/web-api/body/log-fat/) |
| **Sleep** (CSV) | `sleep.json` | ⚠️ Possible | Fitbit API [`POST /1.2/user/-/sleep.json`](https://dev.fitbit.com/build/reference/web-api/sleep/create-sleep-log/) - classic sleep only (no REM/deep/light stages) |
| **Steps** (daily CSV) | `activities-steps.json` | ❌ | No import path (Fitbit doesn't expose step logging in the API) |
| **Calories** (daily CSV) | `activities-calories.json` | ❌ | No import path |
| **Distance** (daily CSV) | `activities-distance.json` | ❌ | No import path |
| **Floors** (daily CSV) | Not converted | ❌ | No import path |
| **Cadence** (from TCX) | Steps derived as `cadence × duration` | ❌ | Not importable; included in JSON for reference |
| **Menstrual health** | Not converted | ❌ | Fitbit Web API has no write endpoint for menstrual/cycle data |

---

## Garmin Input Formats

The converter reads TCX files and CSV exports from Garmin Connect.

### TCX Activities (`activities/*.tcx`)

Standard Garmin TCX v2 format with per-trackpoint heart rate:

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

The reader also extracts `<Cadence>` from trackpoints and derives a step count as `cadence × duration (min)`.

### Body Composition CSV

Garmin Connect data export format:

```
Date,Weight,BMI,BodyFat,BoneMass,MuscleMass,BodyWater
2024-01-15,75.5,23.9,15.8,0,0,0
```

### Sleep CSV

Expected columns: `Date,Sleep Start,Sleep End,Duration (min),Minutes Asleep,Minutes Awake`

```
Date,Sleep Start,Sleep End,Duration (min),Minutes Asleep,Minutes Awake,Efficiency
2024-01-15,2024-01-14 22:45:00,2024-01-15 06:30:00,465,435,30,93
```

### Daily Summary CSV

Expected columns: `Date,Steps,Calories,Distance,Floors,Minutes Sedentary,Minutes Lightly Active,...`

```
Date,Steps,Calories,Distance,Floors,Minutes Sedentary,Minutes Lightly Active
2024-01-15,12400,2520,14300,10,360,240
```

---

## Fitbit Output Formats

### Activities JSON (`activities.json`)

Matches the Google Takeout activity structure:

```json
{
  "activities": [
    {
      "activityName": "Running 2024-01-15 07:30",
      "activityTypeId": 90009,
      "activeDuration": 2750000,
      "calories": 380,
      "distance": 8500.0,
      "distanceUnit": "METERS",
      "steps": 0,
      "startTime": "2024-01-15T07:30:00.000",
      "duration": 2750000,
      "heartRateZones": [
        {"name": "Fat Burn", "min": 95, "max": 134, "minutes": 4, "caloriesOut": 0},
        {"name": "Cardio", "min": 135, "max": 159, "minutes": 3, "caloriesOut": 0}
      ],
      "heartRate": {"average": 126, "max": 155}
    }
  ]
}
```

**Sport type mapping:**

| Garmin Sport | Fitbit activityTypeId |
|---|---|
| Running | 90009 |
| Walking | 90010 |
| Hiking | 90011 |
| Biking / Cycling | 90013 |
| Swimming | 90015 |
| Elliptical | 90016 |
| Weights / Strength | 90017 |
| Yoga | 90018 |
| Cardio / Other | 90028 |

### Weight JSON (`weight.json`)

```json
[
  {"dateTime": "2024-01-15", "value": {"weight": 75.5, "bmi": 23.9, "fat": 15.8}}
]
```

### Sleep JSON (`sleep.json`)

```json
{
  "sleep": [
    {
      "dateOfSleep": "2024-01-15",
      "duration": 27900000,
      "startTime": "2024-01-14T22:45:00.000",
      "endTime": "2024-01-15T06:30:00.000",
      "minutesAsleep": 435,
      "minutesAwake": 30,
      "efficiency": 0,
      "isMainSleep": true,
      "timeInBed": 465,
      "minutesToFallAsleep": 0,
      "levels": {"summary": {}, "data": []}
    }
  ]
}
```

### Daily Field JSONs (`activities-{steps,calories,distance}.json`)

```json
[
  {"dateTime": "2024-01-15", "value": "12400"}
]
```

These match the format that `steps-*.json`, `calories-*.json`, and `distance-*.json` use in a real Fitbit Takeout export.

### TCX Passthrough (`activities/*.tcx`, with `--tcx` flag)

Identical to the original Garmin TCX files, regenerated for direct use with third-party upload tools.

---

## Installation

```bash
# No installation required - run directly:
python -m garmin2fitbit /path/to/garmin/export -o ./fitbit_output

# Or install with pip for use as a command:
pip install -e /path/to/fitbit2garmin
garmin2fitbit /path/to/garmin/export -o ./fitbit_output
```

Requires Python 3.10+. No external dependencies.

---

## Usage

```
usage: python -m garmin2fitbit [-h] [-o OUTPUT_DIR] [--no-activities]
                                [--tcx] [--no-weight] [--no-sleep]
                                [--no-summary] [-v] [--version]
                                input_dir

Convert Garmin data export to Fitbit-compatible formats

positional arguments:
  input_dir             Directory with Garmin TCX files (in activities/)
                        and CSV exports

options:
  -h, --help            show this help message and exit
  -o, --output-dir OUTPUT_DIR
                        Output directory (default: ./fitbit_output)
  --no-activities       Skip Fitbit JSON activities output
  --tcx                 Also generate TCX passthrough files (for Fitbit
                        API upload)
  --no-weight           Skip body composition JSON export
  --no-sleep            Skip sleep JSON export
  --no-summary          Skip daily summary JSON export
  -v, --verbose         Verbose output
  --version             show program's version number and exit
```

### Examples

```bash
# Basic conversion - all data to Fitbit JSON
python -m garmin2fitbit ~/Downloads/Garmin/Export -o ./fitbit_data

# Also generate TCX passthrough files (for third-party upload tools)
python -m garmin2fitbit ~/Downloads/Garmin/Export -o ./fitbit_data --tcx

# Activities + weight only
python -m garmin2fitbit ~/Downloads/Garmin/Export -o ./fitbit_data \
  --no-sleep --no-summary

# TCX passthrough only (no Fitbit JSON at all)
python -m garmin2fitbit ~/Downloads/Garmin/Export -o ./fitbit_data \
  --no-weight --no-sleep --no-summary --tcx

# Round-trip: Fitbit → Garmin TCX → Fitbit JSON
python -m fitbit2garmin ~/Takeout/Fitbit -o ./garmin_output
python -m garmin2fitbit ./garmin_output -o ./back_to_fitbit --tcx
```

---

## Third-Party Import Options

Since Fitbit has no native bulk import, here are the practical options:

| Tool | Platform | Cost | Supports (Write to Fitbit) |
|---|---|---|---|---|
| **Health Sync** | Android, iOS | Paid (lifetime license available) | Steps, heart rate (daily), sleep, weight, body fat, activities; via Google Health APIs |
| **myFitnessSync** | iOS | Paid subscription | Steps, weight, body fat, sleep, water (5 fields); Apple Health → Fitbit |
| **RunGap** | iOS | Subscription after trial | Activities (workouts), daily summaries; 50+ platforms bridged |
| **Fitbit Web API** | Any (scripts) | Free | Activities, weight, body fat, sleep (classic only); see API section below |
| **Manual entry** | Fitbit mobile app | Free | Everything (one-by-one, tedious for bulk) |

### Getting a Fitbit API Token

Fitbit uses OAuth 2.0. You need a **personal app** to get a token:

1. Go to [dev.fitbit.com](https://dev.fitbit.com/) → **Register an App**
2. Set **OAuth 2.0 Application Type** to **Personal**
3. Set **Redirect URL** to `https://localhost` (or anything valid)
4. After registering, note your **Client ID** and **Client Secret**

Then get a token with curl (requires a browser step):

```bash
# 1. Open this URL in your browser, authorize, then copy the code from the redirect
open "https://www.fitbit.com/oauth2/authorize?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=https://localhost&scope=activity+nutrition+heartrate+location+nutrition+profile+settings+sleep+social+weight&expires_in=31536000"

# 2. Exchange the code for an access token
curl -X POST https://api.fitbit.com/oauth2/token \
  -H "Authorization: Basic $(echo -n 'YOUR_CLIENT_ID:YOUR_CLIENT_SECRET' | base64)" \
  -d "grant_type=authorization_code" \
  -d "code=CODE_FROM_STEP_1" \
  -d "redirect_uri=https://localhost"

# 3. Use the returned access_token in the examples below
TOKEN="your_access_token_here"
```

> Personal apps get tokens valid for 1 year. Save your `refresh_token` to renew it.

### Upload Activities (curl)

The `activities.json` output from `garmin2fitbit` is an array. Upload each entry via the Fitbit API:

```bash
TOKEN="your_access_token_here"

# Upload one activity at a time
curl -X POST "https://api.fitbit.com/1/user/-/activities.json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "activityId": 90009,
    "startTime": "2024-01-15T07:30:00",
    "durationMillis": 2750000,
    "distance": 8500,
    "distanceUnit": "METERS",
    "manualCalories": 380
  }'
```

Batch script to upload all activities from `activities.json`:

```bash
TOKEN="your_access_token_here"

cat fitbit_output/activities.json | jq -c '.activities[]' | while read -r act; do
  activityId=$(echo "$act" | jq '.activityTypeId')
  startTime=$(echo "$act" | jq -r '.startTime')
  durationMillis=$(echo "$act" | jq '.duration')
  distance=$(echo "$act" | jq '.distance')
  calories=$(echo "$act" | jq '.calories')
  name=$(echo "$act" | jq -r '.activityName')

  echo "Uploading: $name"

  curl -s -X POST "https://api.fitbit.com/1/user/-/activities.json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "activityId=$activityId" \
    -d "startTime=$startTime" \
    -d "durationMillis=$durationMillis" \
    -d "distance=$distance" \
    -d "distanceUnit=METERS" \
    -d "manualCalories=$calories"

  # Rate limit: 150 requests per hour
  sleep 5
done
```

### Upload Body Composition (curl)

```bash
TOKEN="your_access_token_here"

# Upload weight log
curl -X POST "https://api.fitbit.com/1/user/-/body/log/weight.json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "weight=75.5" \
  -d "date=2024-01-15" \
  -d "time=08:00"

# Upload body fat percentage
curl -X POST "https://api.fitbit.com/1/user/-/body/log/fat.json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "fat=15.8" \
  -d "date=2024-01-15" \
  -d "time=08:00"
```

Batch script from `weight.json`:

```bash
TOKEN="your_access_token_here"

cat fitbit_output/weight.json | jq -c '.[]' | while read -r entry; do
  date=$(echo "$entry" | jq -r '.dateTime')
  weight=$(echo "$entry" | jq -r '.value.weight')
  fat=$(echo "$entry" | jq -r '.value.fat // empty')

  echo "Uploading weight for $date: ${weight}kg"

  curl -s -X POST "https://api.fitbit.com/1/user/-/body/log/weight.json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "weight=$weight" \
    -d "date=$date" \
    -d "time=08:00"

  if [ -n "$fat" ]; then
    curl -s -X POST "https://api.fitbit.com/1/user/-/body/log/fat.json" \
      -H "Authorization: Bearer $TOKEN" \
      -d "fat=$fat" \
      -d "date=$date" \
      -d "time=08:00"
  fi

  sleep 3
done
```

### Upload Sleep (curl)

The Fitbit API can create sleep logs via `POST /1.2/user/-/sleep.json`. Note that this creates **classic sleep** (start time + duration) - no REM/deep/light stage data is preserved.

```bash
TOKEN="your_access_token_here"

# Upload a single sleep log
curl -X POST "https://api.fitbit.com/1.2/user/-/sleep.json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2024-01-15",
    "startTime": "2024-01-14T22:45:00",
    "duration": 27900000
  }'
```

Batch script from `sleep.json`:

```bash
TOKEN="your_access_token_here"

cat fitbit_output/sleep.json | jq -c '.sleep[]' | while read -r entry; do
  date=$(echo "$entry" | jq -r '.dateOfSleep')
  startTime=$(echo "$entry" | jq -r '.startTime' | sed 's/\.000$//')
  duration=$(echo "$entry" | jq -r '.duration')

  echo "Uploading sleep for $date"

  curl -s -X POST "https://api.fitbit.com/1.2/user/-/sleep.json" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"date\":\"$date\",\"startTime\":\"$startTime\",\"duration\":$duration}"

  sleep 5
done
```

### Full Python Upload Script

Save as `upload_to_fitbit.py` alongside your `fitbit_output/` directory:

```python
#!/usr/bin/env python3
"""Upload garmin2fitbit output to Fitbit via the Web API."""

import json
import os
import time
import requests

TOKEN = "your_access_token_here"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
OUTPUT_DIR = "fitbit_output"


def upload_activities():
    path = os.path.join(OUTPUT_DIR, "activities.json")
    if not os.path.exists(path):
        return
    with open(path) as f:
        data = json.load(f)
    for act in data.get("activities", []):
        payload = {
            "activityId": act["activityTypeId"],
            "startTime": act["startTime"],
            "durationMillis": act["duration"],
            "distance": act["distance"],
            "distanceUnit": "METERS",
            "manualCalories": act["calories"],
        }
        print(f"  → {act['activityName']} ...", end=" ")
        r = requests.post(
            "https://api.fitbit.com/1/user/-/activities.json",
            headers=HEADERS, data=payload,
        )
        print("OK" if r.ok else f"FAIL ({r.status_code})")
        time.sleep(5)


def upload_weight():
    path = os.path.join(OUTPUT_DIR, "weight.json")
    if not os.path.exists(path):
        return
    with open(path) as f:
        entries = json.load(f)
    for entry in entries:
        date = entry["dateTime"]
        val = entry["value"]
        print(f"  → Weight {date} ({val['weight']} kg) ...", end=" ")
        r = requests.post(
            "https://api.fitbit.com/1/user/-/body/log/weight.json",
            headers=HEADERS,
            data={"weight": val["weight"], "date": date, "time": "08:00"},
        )
        print("OK" if r.ok else f"FAIL ({r.status_code})")

        if val.get("fat"):
            print(f"  → Body fat {date} ({val['fat']}%) ...", end=" ")
            r = requests.post(
                "https://api.fitbit.com/1/user/-/body/log/fat.json",
                headers=HEADERS,
                data={"fat": val["fat"], "date": date, "time": "08:00"},
            )
            print("OK" if r.ok else f"FAIL ({r.status_code})")

        time.sleep(3)


def upload_sleep():
    path = os.path.join(OUTPUT_DIR, "sleep.json")
    if not os.path.exists(path):
        return
    with open(path) as f:
        data = json.load(f)
    for entry in data.get("sleep", []):
        payload = {
            "date": entry["dateOfSleep"],
            "startTime": entry["startTime"].rstrip(".000"),
            "duration": entry["duration"],
        }
        print(f"  → Sleep {payload['date']} ...", end=" ")
        r = requests.post(
            "https://api.fitbit.com/1.2/user/-/sleep.json",
            headers=HEADERS, json=payload,
        )
        print("OK" if r.ok else f"FAIL ({r.status_code})")
        time.sleep(5)


if __name__ == "__main__":
    print("Uploading activities...")
    upload_activities()
    print("Uploading body composition...")
    upload_weight()
    print("Uploading sleep...")
    upload_sleep()
    print("Done.")
```

### Rate Limits

| Limit | Value |
|---|---|
| Requests per hour (per user) | 150 |
| Requests per day (per user) | 30,000 |

The batch scripts above include `sleep` calls to stay within limits. For large exports, add longer delays or split across multiple days.

### Data Type Import Feasibility by Tool

| Data | Health Sync | myFitnessSync | RunGap | Fitbit API | Manual |
|---|---|---|---|---|---|
| **Steps** (daily) | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Heart rate** (daily/resting) | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Heart rate** (intraday) | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Sleep** (classic) | ✅ | ✅ | ❌ | ✅ | ✅ |
| **Sleep** (stages) | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Menstrual cycle** | ❌ | ❌ | ❌ | ❌ | ✅ (app only) |
| **Activities** (workouts) | ✅ | ❌ | ✅ | ✅ | ✅ |
| **Weight / Body fat** | ✅ | ✅ | ❌ | ✅ | ✅ |

> **Note**: Health Sync uses the newer Google Health APIs (post-Fitbit migration). If your account hasn't migrated, features may differ. myFitnessSync writes via Apple Health → Fitbit bridge and is iOS-only.

---

## Setting Up Garmin Export

1. Go to [Garmin Connect](https://connect.garmin.com/) → **Settings** (gear icon) → **Data Management**
2. Click **Export Your Data** and wait for the email
3. Download and extract the ZIP
4. The converter expects:
   - TCX files inside an `activities/` subdirectory under `input_dir`
   - CSV files (body composition, sleep, daily summary) at the top level of `input_dir`

Alternatively, point it at any directory containing TCX files in an `activities/` folder (like the output from `fitbit2garmin`):

```bash
python -m fitbit2garmin ~/Takeout/Fitbit -o ./garmin_output
python -m garmin2fitbit ./garmin_output -o ./fitbit_formatted --tcx
```

---

## Limitations

| Limitation | Details |
|---|---|
| **No bulk import into Fitbit** | Fitbit does not provide a CSV/TCX upload feature. The JSON output is for archival or API consumption |
| **Sleep: classic only** | The API accepts sleep logs via `POST /1.2/user/-/sleep.json`, but only classic sleep (start time + duration) - no REM/deep/light stage data |
| **Daily steps/calories cannot be imported** | Fitbit's API does not support logging daily totals for steps, calories, or distance |
| **Heart rate cannot be imported standalone** | No API endpoint exists to upload HR data; it can only be carried by TCX via third-party tools |
| **Menstrual health cannot be imported** | Fitbit Web API has no write endpoint for cycle or menstrual health data |
| **No HRV / Stress / SpO2** | Garmin's advanced metrics are not converted to Fitbit equivalents |
| **No GPS trackpoints** | TCX-to-JSON conversion keeps heart rate data but GPS coordinates are not extracted |
| **Sleep efficiency defaulted to 0** | Garmin sleep CSVs don't include an efficiency score; the field is written as 0 |

---

[Back to main README](../README.md)
