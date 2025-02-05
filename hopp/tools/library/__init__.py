from pathlib import Path

LIBRARY_DIR = Path(__file__).resolve().parent
PV_LIB = LIBRARY_DIR/"pv"
WIND_LIB = LIBRARY_DIR/"wind"
TURBINE_LIB = WIND_LIB/"turbine_designs"
WIND_FARM_LIB = WIND_LIB/"wind_farm_layouts"