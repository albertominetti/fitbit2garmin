"""Allow running as python -m fitbit2garmin."""

from .converter import main

if __name__ == "__main__":
    raise SystemExit(main())
