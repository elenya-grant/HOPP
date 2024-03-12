import os
from hopp.utilities import load_yaml
import pandas as pd
import numpy as np
import copy
from greenheart.simulation.technologies.hydrogen.electrolysis.run_h2_PEM import run_h2_PEM
def update_site(hopp_config,site_data,hub_height):
    hopp_config['site']['data']['lat'] = site_data['latitude']
    hopp_config['site']['data']['lon'] = site_data['longitude']
    hopp_config['site']['hub_height'] = hub_height
    return hopp_config

def update_technology_capacities(hopp_config,site_data):
    
    turbine_size_mw = hopp_config['technologies']['wind']['turbine_rating_kw']/1000
    n_turbines = int(site_data['wind_size_mw']/turbine_size_mw)
    hopp_config['technologies']['pv']['system_capacity_kw'] = 1000*site_data['solar_size_mw']
    hopp_config['technologies']['wind']['num_turbines'] = n_turbines

    return hopp_config

def get_wind_info(turbine_model,input_dir):
    yaml_filename = os.path.join(input_dir, turbine_model + '.yaml')
    csv_filename = os.path.join(input_dir, turbine_model + '.csv')
    power_curve = pd.read_csv(csv_filename)
    turb_params = load_yaml(yaml_filename)
    turb_params['hub_height']
    turb_params['rotor_diameter']
    return turb_params,power_curve

def set_wind_info(hi,params_config_init,input_dir):
    params_config = copy.deepcopy(params_config_init)
    turb_params,power_curve = get_wind_info(params_config['wind']['Turbine']['turbine_model'],input_dir)
    params_config['wind']['Turbine'].pop('turbine_model')
    # params_config['wind'].pop('sim_default_losses')
    params_config['wind']['Turbine']['wind_turbine_powercurve_powerout'] = power_curve['Power [kW]'].to_list()
    params_config['wind']['Turbine']['wind_turbine_powercurve_windspeeds'] = power_curve['Wind Speed [m/s]'].to_list()
    params_config['wind']['Turbine']["wind_turbine_rotor_diameter"] = turb_params['rotor_diameter']
    params_config['wind']['Turbine']["wind_turbine_hub_ht"] = turb_params['hub_height']
    hi.hopp.system.wind._system_model.assign(params_config['wind'])
    hi.system.wind._system_model.assign(params_config['wind'])
    
    turb_params['hub_height']
    return hi

def get_hybrid_plant_power(hi):
    solar_plant_power_kW = np.array(hi.system.pv.generation_profile)
    wind_plant_power_kW = np.array(hi.system.wind.generation_profile)
    hybrid_plant_generation_profile = solar_plant_power_kW + wind_plant_power_kW
    return hybrid_plant_generation_profile

def get_hydrogen_storage_SOC(hydrogen_production_kg_pr_hr):
    h2_dmd = np.mean(hydrogen_production_kg_pr_hr)
    diff = hydrogen_production_kg_pr_hr - h2_dmd
    h2_soc = np.cumsum(diff)
    # h2_soc = np.insert(h2_soc,0,0)
    h2_storage_size_kg = np.max(h2_soc) - np.min(h2_soc)
    return h2_soc

def run_electrolyzer(hybrid_plant_generation_profile,params_config,site_data):
    electrolyzer_size_mw = site_data['electrolyzer_size_mw']
    stack_size_MW = params_config['electrolyzer']['stack_size_MW']
    use_degradation_penalty = params_config['electrolyzer']['include_degradation_penalty']
    number_electrolyzer_stacks = int(electrolyzer_size_mw/stack_size_MW)
    grid_connection_scenario = 'off-grid'
    pem_control_type = 'basic'
    user_defined_pem_param_dictionary = {
        "Modify BOL Eff": False,
        "BOL Eff [kWh/kg-H2]": [],
        "Modify EOL Degradation Value": True,
        "EOL Rated Efficiency Drop": params_config['electrolyzer']['EOL_eff_drop'],
    }
    h2_results, H2_Timeseries, H2_Summary,energy_input_to_electrolyzer = \
    run_h2_PEM(hybrid_plant_generation_profile,
    electrolyzer_size_mw,
    params_config['plant']['useful_life'], 
    number_electrolyzer_stacks,
    [],
    pem_control_type,
    100,
    user_defined_pem_param_dictionary,
    use_degradation_penalty,
    grid_connection_scenario,
    [])
    return h2_results,H2_Timeseries

def make_timeseries_df(H2_soc,H2_demand,h2_prod,site_index,state):
    df = pd.DataFrame({'H2 SOC [kg]':H2_soc,'H2 Demand [kg]':H2_demand,'H2 Production [kg]':h2_prod})
    df = df.T
    site_id = '{}-{}'.format(site_index,state)
    df.index = [[site_id,site_id,site_id],['H2 SOC [kg]','H2 Demand [kg]','H2 Production [kg]']]
    return df

def make_site_detailed_results(h2_results,H2_Timeseries,hybrid_plant_generation,site_index,state,site_output_dir):
    
    df = pd.concat([pd.Series(h2_results),H2_Timeseries,pd.Series({'Hybrid Plant Generation [kWh]':hybrid_plant_generation})])
    site_id = '{}-{}_Results.pkl'.format(site_index,state)
    filepath = os.path.join(site_output_dir,site_id)
    df.to_pickle(filepath)
