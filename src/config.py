"""Paths and constants for the hantavirus spread modeling project."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
MODELS_DIR = ROOT / "models"
OUTPUTS = ROOT / "outputs" / "figures"

START_YEAR = 1993
END_YEAR = 2023
RANDOM_STATE = 42

# CDC surveillance regions (MacNeil et al., Emerg Infect Dis 2011)
REGIONS = {
    "Southwest": ["AZ", "CA", "CO", "NM", "NV", "UT"],
    "Northwest": ["ID", "MT", "OR", "WA", "WY"],
    "Midwest": ["IL", "IN", "IA", "KS", "LA", "MN", "ND", "NE", "OK", "SD", "TX", "WI"],
    "East": ["FL", "MD", "NC", "NY", "PA", "VA", "WV"],
}

# Representative coordinates (state centroid approx.) for Open-Meteo
STATE_COORDS = {
    "AZ": (34.05, -111.09),
    "CA": (36.78, -119.42),
    "CO": (39.55, -105.78),
    "NM": (34.52, -106.25),
    "NV": (38.80, -116.42),
    "UT": (39.32, -111.09),
    "ID": (44.07, -114.74),
    "MT": (46.88, -110.36),
    "OR": (43.80, -120.55),
    "WA": (47.75, -120.74),
    "WY": (43.08, -107.29),
    "IL": (40.63, -89.40),
    "IN": (40.27, -86.13),
    "IA": (41.88, -93.10),
    "KS": (38.53, -98.38),
    "LA": (30.98, -91.96),
    "MN": (46.73, -94.69),
    "ND": (47.55, -101.00),
    "NE": (41.49, -99.90),
    "OK": (35.47, -97.52),
    "SD": (44.30, -99.44),
    "TX": (31.97, -99.90),
    "WI": (44.27, -89.62),
    "FL": (27.66, -81.52),
    "MD": (39.05, -76.64),
    "NC": (35.76, -79.02),
    "NY": (42.17, -74.95),
    "PA": (40.59, -77.21),
    "VA": (37.43, -78.66),
    "WV": (38.64, -80.62),
}

STATE_TO_REGION = {
    st: region for region, states in REGIONS.items() for st in states
}

# Approximate long-run share of US cases by state (from CDC maps + EID regional splits)
STATE_CASE_WEIGHTS = {
    "CO": 0.14,
    "NM": 0.12,
    "AZ": 0.11,
    "CA": 0.10,
    "WA": 0.08,
    "MT": 0.07,
    "UT": 0.06,
    "NV": 0.05,
    "ID": 0.05,
    "OR": 0.04,
    "WY": 0.04,
    "TX": 0.03,
    "NE": 0.02,
    "SD": 0.02,
    "ND": 0.02,
    "WI": 0.02,
    "MN": 0.02,
    "KS": 0.02,
    "OK": 0.01,
    "IA": 0.01,
    "IN": 0.01,
    "IL": 0.01,
    "LA": 0.01,
    "NY": 0.02,
    "PA": 0.01,
    "WV": 0.01,
    "VA": 0.01,
    "NC": 0.01,
    "MD": 0.01,
    "FL": 0.01,
}
