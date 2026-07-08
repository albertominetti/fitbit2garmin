"""Allow running as python -m garmin2fitbit."""

from .converter import main

if __name__ == "__main__":
    raise SystemExit(main())
