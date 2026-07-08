from setuptools import setup

setup(
    name="fitbit2garmin",
    version="1.0.0",
    packages=["fitbit2garmin"],
    entry_points={
        "console_scripts": [
            "fitbit2garmin=fitbit2garmin.converter:main",
        ],
    },
    python_requires=">=3.10",
)
