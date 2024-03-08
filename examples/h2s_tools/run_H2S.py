from hopp.utilities.keys import set_nrel_key_dot_env
from hopp.simulation import HoppInterface
from hopp.utilities import load_yaml
set_nrel_key_dot_env()
import pandas as pd
import numpy as np
import os
from h2s_tools.tools import update_site, update_technology_capacities, set_wind_info,get_hybrid_plant_power,run_electrolyzer,get_hydrogen_storage_SOC,make_timeseries_df,make_site_detailed_results
from h2s_tools.tools import get_wind_info
save_site_details = True

this_dir = os.path.dirname(__file__)
input_dir = os.path.join(this_dir,"input_files")
output_dir = os.path.join(this_dir,"outputs")
site_specific_output_dir = os.path.join(output_dir,"site_specific_outputs")

output_ts_filename = '50sites_H2SOC_Timeseries_Outputs.csv'
config_filename = 'H2S-default-config.yaml'
params_filename = 'assumptions.yaml'
final_sitelist_filename = '50sites_H2S_detailed.csv'


site_df = pd.read_csv(os.path.join(input_dir,final_sitelist_filename),index_col='Unnamed: 0')
site_df = site_df.drop('desal_size_kg_pr_sec',axis=1)
params_config = load_yaml(os.path.join(input_dir,params_filename))
hopp_config = load_yaml(os.path.join(input_dir,config_filename))

res_df = pd.DataFrame()
turb_params,power_curve = get_wind_info(params_config['wind']['Turbine']['turbine_model'],input_dir)
print("-------------------------")
print("Starting Hydrogen Storage Runs...")
print("-------------------------")
for i in range(len(site_df)):
    config = update_site(hopp_config,site_df.iloc[i],turb_params['hub_height'])
    config = update_technology_capacities(config,site_df.iloc[i])
    hi_init = HoppInterface(config)
    hi = set_wind_info(hi_init,params_config,input_dir)
    hi.simulate()
    hybrid_plant_generation_profile = get_hybrid_plant_power(hi)
    
    h2_results,H2_Timeseries = run_electrolyzer(hybrid_plant_generation_profile,params_config,site_df.iloc[i])
    H2_demand = np.ones(8760)*np.mean(H2_Timeseries['hydrogen_hourly_production'])
    H2_soc = get_hydrogen_storage_SOC(H2_Timeseries['hydrogen_hourly_production'])
    
    site_res_df = make_timeseries_df(H2_soc,H2_demand,H2_Timeseries['hydrogen_hourly_production'],i,site_df.iloc[i]['state'])
    res_df = pd.concat([res_df,site_res_df],axis=0)
    site_desc = '({}, {}) - {}'.format(site_df.iloc[i]['latitude'],site_df.iloc[i]['longitude'],site_df.iloc[i]['state'])
    if save_site_details:
        make_site_detailed_results(h2_results,H2_Timeseries,hybrid_plant_generation_profile,i,site_df.iloc[i]['state'],site_specific_output_dir)
    print("Completed run {} of {}, used site {}".format(i+1,len(site_df),site_desc))
    []
output_ts_filepath = os.path.join(output_dir,output_ts_filename)
res_df.to_csv(output_ts_filepath)
print("-------------------------")
print("Completed all site runs")
print("Saved Timeseries outputs to: \n {}".format(output_ts_filepath))
print("-------------------------")
print("-------------------------")
[]

