# (running) stride and cadence app
An app to evaluate running mechanics from Garmin data, allowing the study of how stride length and cadence evolve versus running speed.

## About
This streamlit-based web app allows to analyze running data from a Garmin Connect account. Data retrieval is handled using cyberjunky's python-garminconnect API wrapper (https://github.com/cyberjunky/python-garminconnect.git).

## Installation
Apart from streamlit and other well-known packages, python-garminconnect should be also installed via
```
pip install garminconnect
```
## Execution

```
streamlit run app.py
```
