from scipy.constants import R, g, convert_temperature

def calculate_air_density_for_elevation(elevation_m:float):
    """calculate air density based on site elevation using the Barometric formula.
    this function is based on Equation 1 from: https://en.wikipedia.org/wiki/Barometric_formula#Density_equations
    
    Args:
        elevation_m (float): elevation of site in meters

    Returns:
        rho (float): air density in kg/m3 at elevation of site
    """
    rho0 = 1.225 # air density at sea level (kg/m3)
    t_ref = 20 # standard air temperature (Celsius)
    elevation_sea_level = 0.0 #reference elevation at sea level (m)
    l = 0.0065 # temperature lapse null rate (K/m) for 0-11000m above sea level
    molar_mass_air = 28.96 # molar mass of air (g/mol)
    
    # convert temperature to Kelvin
    T_ref = convert_temperature([t_ref], "C", "K")[0] 
    
    # exponent value used in equation below
    e = g*(molar_mass_air/1e3)/(R*l) 
    # g: acceleration due to gravity (m/s2)
    # R: universal gas constant (J/mol-K)
    
    # calculate air density at site elevation
    rho = rho0*((T_ref - ((elevation_m-elevation_sea_level)*l))/T_ref)**(e - 1)
    return rho

def calculate_elevation_air_density_losses(elevation_m:float):
    rho0 = 1.225
    air_density = calculate_air_density_for_elevation(elevation_m)
    loss_ratio = 1 - (air_density/rho0)
    loss_percent = loss_ratio*100
    return loss_percent
