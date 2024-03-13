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
    # n_turbines = int(site_data['wind_size_mw']/turbine_size_mw)
    n_turbines = int(site_data['Wind Size [MW]']/turbine_size_mw)
    # hopp_config['technologies']['pv']['system_capacity_kw'] = 1000*site_data['solar_size_mw']
    hopp_config['technologies']['pv']['system_capacity_kw'] = 1000*site_data['Solar Size [MW]']
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
    hi.hopp.system.wind._system_model.assign(params_config['wind'])
    hi.system.wind._system_model.assign(params_config['wind'])
    # hi.system.wind._system_model.Losses.assign({'avail_turb_loss':0.58})
    # hi.hopp.system.wind._system_model.Losses.assign({'avail_turb_loss':0.58})
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
    electrolyzer_size_mw = params_config['electrolyzer']['electrolyzer_size_mw']
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

def make_site_detailed_results(h2_results,H2_Timeseries,hi,hybrid_plant_generation,site_index,site_info,site_output_dir):
    
    pv_gen = pd.Series({'Solar Generation [kWh]':np.array(hi.system.pv.generation_profile)})
    wind_gen = pd.Series({'Wind Generation [kWh]':np.array(hi.system.wind.generation_profile)})
    hybrid_gen = pd.Series({'Hybrid Plant Generation [kWh]':hybrid_plant_generation})
    pv_aep = np.sum(hi.system.pv.generation_profile)
    wind_aep = np.sum((hi.system.wind.generation_profile))
    hybrid_aep = np.sum(hybrid_plant_generation)
    wind_cf = wind_aep/(site_info['Wind Size [MW]']*1000*8760)
    pv_cf = pv_aep/(site_info['Solar Size [MW]']*1000*8760)
    keys = ['Wind AEP [kWh/yr]','Solar AEP [kWh/yr]','Wind CF [-]','PV CF [-]','Hybrid AEP [kWh/yr]']
    vals = [wind_aep,pv_aep,wind_cf,pv_cf,hybrid_aep]
    hpp_res = dict(zip(keys,vals))
    # df = pd.concat([pd.Series(h2_results),H2_Timeseries,pd.Series({'Hybrid Plant Generation [kWh]':hybrid_plant_generation})])
    df = pd.concat([pd.Series(h2_results),H2_Timeseries,pv_gen,wind_gen,hybrid_gen,pd.Series(hpp_res)])
    site_id = '{}b-{}_Results.pkl'.format(site_index,site_info['state'])
    filepath = os.path.join(site_output_dir,site_id)
    df.to_pickle(filepath)

def debug_negative_H2SOC(hydrogen_production_kg_pr_hr):
    H2_demand = np.mean(hydrogen_production_kg_pr_hr)
    diff = hydrogen_production_kg_pr_hr - H2_demand
    Charge = np.where(diff>0,diff,0)
    Discharge = np.where(diff<0,-1*diff,0)
    idx_more_charge=[i for i in range(2,len(Charge)) if np.sum(Charge[:i])>np.sum(Discharge[:i])]
    
    i = idx_more_charge[0]
    first_charge = np.flip(Charge[:i])
    delta_i_start = np.argwhere(first_charge==0)[0][0]

    i_start = i - delta_i_start
    
    H2_istart = hydrogen_production_kg_pr_hr[i_start]
    H2_istart_1 = hydrogen_production_kg_pr_hr[i_start-1]
    H2_end = hydrogen_production_kg_pr_hr[-1]
    H2_start = hydrogen_production_kg_pr_hr[0]
    h2_tot_first_half = np.sum(hydrogen_production_kg_pr_hr[i_start:])
    h2_tot_second_half = np.sum(hydrogen_production_kg_pr_hr[:i_start])

    i_new_start = len(hydrogen_production_kg_pr_hr[i_start:])
    new_h2_prod = np.zeros(8760)
    new_h2_prod[0:i_new_start] = hydrogen_production_kg_pr_hr[i_start:]
    new_h2_prod[i_new_start:] = hydrogen_production_kg_pr_hr[:i_start]

    check = 0
    if H2_istart == new_h2_prod[0]:
        check +=1
    if H2_istart_1 == new_h2_prod[-1]:
        check +=1
    if H2_start == new_h2_prod[i_new_start]:
        check +=1
    if H2_end == new_h2_prod[i_new_start-1]:
        check +=1
    if np.sum(new_h2_prod) == np.sum(hydrogen_production_kg_pr_hr):
        check +=1
    
    new_diff = new_h2_prod - H2_demand
    Charge = np.where(new_diff>0,new_diff,0)
    Discharge = np.where(new_diff<0,-1*new_diff,0)
    h2_soc = np.cumsum(new_diff)
    H2_soc = Charge-Discharge
    H2_soc = np.zeros(8760)
    idx_charge = np.argwhere(new_diff>0)[:,0]
    idx_discharge = np.argwhere(new_diff<0)[:,0]


