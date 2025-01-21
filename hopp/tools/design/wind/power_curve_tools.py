import numpy as np


def calculate_cp_from_power(wind_speeds_ms,power_curve_kw,rotor_diameter,air_density = 1.225):
    rotor_area = np.pi*((rotor_diameter/2)**2)
    if isinstance(wind_speeds_ms,list):
        wind_speeds_ms = np.array(wind_speeds_ms)
    if isinstance(power_curve_kw,list):
        power_curve_kw = np.array(power_curve_kw)
    # power available in the wind (kW)
    p_wind = 0.5*air_density*rotor_area*(wind_speeds_ms**3)/1e3
    cp = list(power_curve_kw/p_wind)
    return cp

def calculate_power_from_cp(wind_speeds_ms,cp_curve,rotor_diameter,air_density = 1.225):
    rotor_area = np.pi*((rotor_diameter/2)**2)
    if isinstance(wind_speeds_ms,list):
        wind_speeds_ms = np.array(wind_speeds_ms)
    if isinstance(cp_curve,list):
        cp_curve = np.array(cp_curve)
    # power available in the wind (kW)
    p_wind = 0.5*air_density*rotor_area*(wind_speeds_ms**3)/1e3
    power_kW = list(cp_curve*p_wind)
    return power_kW

def estimate_thrust_coefficient(wind_speeds_ms,cp_curve):
    #NOTE: this is a placeholder function!
    ct_curve = list(np.zeros(len(wind_speeds_ms)))
    return ct_curve