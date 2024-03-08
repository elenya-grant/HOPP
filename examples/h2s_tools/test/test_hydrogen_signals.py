import pandas as pd
import os
import numpy as np
from hopp.utilities.keys import set_nrel_key_dot_env
from hopp.simulation import HoppInterface
from hopp.utilities import load_yaml
set_nrel_key_dot_env()
from test_tools import update_site, update_technology_capacities, set_wind_info,get_hybrid_plant_power,run_electrolyzer,get_hydrogen_storage_SOC
from test_tools import get_wind_info
# TX_site = {'state':'Texas','latitude':33.783,'longitude':-96.709}
# KY_site = {'state':'Kentucky','latitude':37.067,'longitude':-82.853}
def calc_RMSE(sim_vals,test_vals):
    if isinstance(test_vals,float):
        rmse = np.sqrt((sim_vals - test_vals)**2)
    else:
        n = len(test_vals)
        error = [(sim_vals[i]-test_vals[i])**2 for i in range(n)]
        rmse = np.sqrt((1/n)*np.sum(error))
    return rmse
def calc_percent_error(sim_val,test_val):
    percent_error = 100*((sim_val-test_val)/test_val)
    return round(percent_error,3)
dirname = os.path.dirname(__file__)
# os.path.abspath(os.path.join(dirname,"../"))
input_root_dir = os.path.abspath(os.path.join(dirname,"../input_files/"))
params_filename = 'assumptions.yaml'
config_filename = 'H2S-default-config.yaml'
test_sitelist_filename = 'TEST_SiteList.csv'

# pd.DataFrame([TX_site,KY_site])
# sites = {'TX':TX_site,'KY':KY_site}

site_df = pd.read_csv(os.path.join(dirname,test_sitelist_filename),index_col='Unnamed: 0')
site_df = site_df.drop('desal_size_kg_pr_sec',axis=1)
params_config = load_yaml(os.path.join(input_root_dir,params_filename))
hopp_config = load_yaml(os.path.join(input_root_dir,config_filename))
turb_params,power_curve = get_wind_info(params_config['wind']['Turbine']['turbine_model'],input_root_dir)

for i in range(len(site_df)):
    state = site_df.iloc[i]['state']
    lat = site_df.iloc[i]['latitude']
    lon = site_df.iloc[i]['longitude']
    test_filename = '{}_{}_{}_H2Timeseries.csv'.format(state,lat,lon)
    test_res = pd.read_csv(os.path.join(dirname,test_filename),index_col = 'Unnamed: 0')
    print("Running test for {}".format(state))
    

    config = update_site(hopp_config,site_df.iloc[i],turb_params['hub_height'])
    config = update_technology_capacities(config,site_df.iloc[i])
    hi_init = HoppInterface(config)
    hi = set_wind_info(hi_init,params_config,input_root_dir)
    hi.simulate()
    hybrid_plant_generation_profile = get_hybrid_plant_power(hi)
    h2_results,H2_Timeseries = run_electrolyzer(hybrid_plant_generation_profile,params_config,site_df.iloc[i])
    h2_hourly_kg = H2_Timeseries['hydrogen_hourly_production']
    h2_dmd = np.mean(h2_hourly_kg)
    H2_soc = get_hydrogen_storage_SOC(H2_Timeseries['hydrogen_hourly_production'])
    H2_storage_size_sim = np.max(H2_soc) - np.min(H2_soc)
    
    test_res["Hydrogen Produced [kg/hr]"].values
    test_res["Hydrogen Demand [kg]"].mean()
    test_res["H2 Storage SOC [kg]"].values
    H2_storage_size_test = test_res["H2 Storage SOC [kg]"].max() - test_res["H2 Storage SOC [kg]"].min()

    rmse_h2_storage_size = calc_RMSE(H2_storage_size_sim,H2_storage_size_test)
    error_perc_storage_size = calc_percent_error(H2_storage_size_sim,H2_storage_size_test)
    
    rmse_h2_dmd = calc_RMSE(h2_dmd,test_res["Hydrogen Demand [kg]"].mean())
    error_perc_h2_dmd = calc_percent_error(h2_dmd,test_res["Hydrogen Demand [kg]"].mean())
    
    rmse_h2_production = calc_RMSE(h2_hourly_kg,test_res["Hydrogen Produced [kg/hr]"].values)
    rmse_h2_soc = calc_RMSE(H2_soc,test_res["H2 Storage SOC [kg]"].values)
    print("-------ERROR RESULTS------------")
    print("Hub-height = {} for {} turbine".format(turb_params['hub_height'],turb_params['turbine_type']))
    print("{} RMSE:".format(state))
    print("H2 Storage Size Error: {} kg or {}%".format(round(H2_storage_size_sim - H2_storage_size_test,3),error_perc_storage_size))
    print("H2 Demand Error: {} kg or {}%".format(round(h2_dmd - test_res["Hydrogen Demand [kg]"].mean(),3),error_perc_h2_dmd))
    print("RMSE Error for H2 Production: {}".format(round(rmse_h2_production,3)))
    print("RMSE Error for H2 SOC: {}".format(round(rmse_h2_soc,3)))
    print("-------------------------")
    []
[]
