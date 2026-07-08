# fitbit2garmin

Bidirectional converter between Fitbit and Garmin data formats.

After years using Fitbit for activity tracking, heart rate monitoring, sleep analysis, and weight logging, migrating to Garmin means leaving your history behind — unless you bring it with you. This project provides tools to translate your health data across platforms.

---

## Tools

### [`fitbit2garmin` →](fitbit2garmin/README.md)

Convert your Fitbit Google Takeout export into TCX and CSV files that Garmin Connect can import. Supports activities (with heart rate), body composition, sleep records, and daily summaries.

### [`garmin2fitbit` →](garmin2fitbit/README.md)

Convert Garmin data exports (TCX activities, CSV body/sleep/summaries) into Fitbit's native JSON format — the same structure used by Google Takeout. Useful for archiving or feeding into third-party tools that use the Fitbit Web API.

---

## Sample Data

The `sample/` directory contains representative data for both converters:

```
sample/
├── input/                          ← Fitbit export (Google Takeout JSON)
├── output/                         ← fitbit2garmin output
├── garmin_input/                   ← Garmin export (TCX + CSV)
└── garmin_output/                  ← garmin2fitbit output
```

Regenerate all sample output:

```bash
python -m fitbit2garmin sample/input -o sample/output
python -m garmin2fitbit sample/garmin_input -o sample/garmin_output
```

---

## Project Structure

```
├── README.md                       ← This file
├── setup.py
├── sample/
│   ├── input/                      ← Sample Fitbit Takeout export
│   ├── output/                     ← Generated Garmin-compatible files
│   ├── garmin_input/               ← Sample Garmin export
│   └── garmin_output/              ← Generated Fitbit-format files
├── fitbit2garmin/                  ← Fitbit → Garmin
│   ├── README.md
│   ├── __init__.py
│   ├── __main__.py
│   ├── models.py
│   ├── reader.py
│   ├── writer.py
│   └── converter.py
└── garmin2fitbit/                  ← Garmin → Fitbit
    ├── README.md
    ├── __init__.py
    ├── __main__.py
    ├── models.py
    ├── reader.py
    ├── writer.py
    └── converter.py
```

Requires Python 3.10+. No external dependencies.
