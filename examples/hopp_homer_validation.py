from pathlib import Path
from hybrid.sites import SiteInfo, flatirons_site
from hybrid.hybrid_simulation import HybridSimulation
from hybrid.dispatch.plot_tools import plot_battery_output, plot_battery_dispatch_error, plot_generation_profile
from hybrid.keys import set_nrel_key_dot_env
# Set API key
set_nrel_key_dot_env()

examples_dir = Path(__file__).parent.absolute()

solar_size_mw = 0.430
wind_size_mw = 1.5
battery_capacity_mw = 1
battery_capacity_mwh = 1
interconnection_size_mw = 2
hub_height = 80
rotor_diameter = 77


technologies = {
    'pv': {
        'system_capacity_kw': solar_size_mw * 1000,
    }, 
    'wind': {
        'num_turbines': 1,
        'turbine_rating_kw': wind_size_mw * 1000,
        'hub_height': hub_height,
        'rotor_diameter': rotor_diameter
    },
    'battery': {
        'system_capacity_kwh': battery_capacity_mw * 1000,
        'system_capacity_kw': battery_capacity_mwh  * 1000
    }
}

# Get resource
lat = flatirons_site['lat']
lon = flatirons_site['lon']
wind_resource_file = examples_dir.parent / "examples" / "resource_files" / "hopp_validation_wind_data.srw"
solar_resource_file = examples_dir.parent / "examples" / "resource_files" / "hoop_validation_solar_data.csv"
load_profile = examples_dir.parent / "resource_files" / "grid" / "hopp_validation_load.csv"
# prices_file = examples_dir.parent / "resource_files" / "grid" / "pricing-data-2015-IronMtn-002_factors.csv"

site = SiteInfo(flatirons_site, solar_resource_file = solar_resource_file, wind_resource_file= wind_resource_file, 
                hub_height=80, desired_schedule = load_profile)
# site = SiteInfo(flatirons_site,
#                 grid_resource_file=prices_file)
# Create base model
hybrid_plant = HybridSimulation(technologies, site, interconnect_kw=interconnection_size_mw * 1000)

hybrid_plant.pv.system_capacity_kw = solar_size_mw * 1000
hybrid_plant.pv.dc_degradation = (0,)             # year over year degradation

hybrid_plant.wind.wake_model = 3                # constant wake loss, layout-independent
hybrid_plant.wind.value("wake_int_loss", 1)     # percent wake loss
hybrid_plant.wind.system_capacity_by_num_turbines(wind_size_mw * 1000)

hybrid_plant.battery._system_model.value("minimum_SOC", 20.0)
hybrid_plant.battery._system_model.value("maximum_SOC", 90.0)
hybrid_plant.battery._system_model.value("initial_SOC", 90.0)


# prices_file are unitless dispatch factors, so add $/kwh here
hybrid_plant.ppa_price = 0.04

# use single year for now, multiple years with battery not implemented yet
hybrid_plant.simulate(project_life=20)

print("output after losses over gross output",
      hybrid_plant.wind.value("annual_energy") / hybrid_plant.wind.value("annual_gross_energy"))

# Save the outputs
annual_energies = hybrid_plant.annual_energies
npvs = hybrid_plant.net_present_values
revs = hybrid_plant.total_revenues
print(annual_energies)
print(npvs)
print(revs)


file = 'figures/'
tag = 'simple2_'
#plot_battery_dispatch_error(hybrid_plant, plot_filename=file+tag+'battery_dispatch_error.png')
'''
for d in range(0, 360, 5):
    plot_battery_output(hybrid_plant, start_day=d, plot_filename=file+tag+'day'+str(d)+'_battery_gen.png')
    plot_generation_profile(hybrid_plant, start_day=d, plot_filename=file+tag+'day'+str(d)+'_system_gen.png')
'''
plot_battery_dispatch_error(hybrid_plant)
plot_battery_output(hybrid_plant)
plot_generation_profile(hybrid_plant)
#plot_battery_dispatch_error(hybrid_plant, plot_filename=tag+'battery_dispatch_error.png')
