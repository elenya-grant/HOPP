# from hybrid.PEM_H2_LT_electrolyzer import PEM_electrolyzer_LT
from numpy.lib.function_base import average
import examples.H2_Analysis.H2AModel as H2AModel
import numpy as np
import pandas as pd
from hybrid.PEM_Model_2Push.run_PEM_master import run_PEM_clusters
def clean_up_final_outputs(h2_tot,h2_ts):
  
   new_h2_tot = h2_tot.drop(['Cluster Rated H2 Production [kg/hr]','Cluster Rated Power Consumed [kWh]','Cluster Rated H2 Production [kg/yr]',\
      'Stack Rated H2 Production [kg/hr]','Stack Rated Power Consumed [kWh]'])
   h2_ts.sum(axis=1)
   ts_sum_desc = ['Input Power [kWh]','Power Consumed [kWh]',\
      'hydrogen production no start-up time','hydrogen_hourly_production',\
         'water_hourly_usage_gal','water_hourly_usage_kg','Stacks on']
   
   new_h2_ts = h2_ts.drop(['V_cell With Deg','Power Per Stack [kW]','Stack Current [A]'])
   new_h2_ts = new_h2_ts.loc[ts_sum_desc].sum(axis=1)
   
   # new_h2_ts.loc[ts_avg_desc].mean(axis=1)
   # pd.concat([new_h2_ts.loc[ts_sum_desc].sum(axis=1),new_h2_ts.loc[ts_avg_desc].mean(axis=1)])
   return new_h2_ts,new_h2_tot
  
def run_h2_PEM(electrical_generation_timeseries, electrolyzer_size,
                useful_life, n_pem_clusters,  electrolysis_scale, 
                pem_control_type,electrolyzer_direct_cost_kw, user_defined_pem_param_dictionary,
                use_degradation_penalty, grid_connection_scenario,
                hydrogen_production_capacity_required_kgphr
                ):
   debug_mode = False
   pem=run_PEM_clusters(electrical_generation_timeseries,electrolyzer_size,n_pem_clusters,electrolyzer_direct_cost_kw,useful_life,user_defined_pem_param_dictionary,use_degradation_penalty)

   if grid_connection_scenario!='off-grid':
      h2_ts,h2_tot=pem.run_grid_connected_pem(electrolyzer_size,hydrogen_production_capacity_required_kgphr)
   else:
      if pem_control_type == 'optimize':
         h2_ts,h2_tot=pem.run(optimize=True)
      else:
         h2_ts,h2_tot=pem.run()
   #avg_pem_cf = np.mean(h2_tot.loc['PEM Capacity Factor'].values)
   # stack_life_df,reformatted_life_df = clean_up_lifetime_performance(h2_tot,use_degradation_penalty)
   # stack_life_df.mean(axis=1).loc[stack_life_spec_desc]
   # cluster_avg_df[stack_life_spec_desc]
   
   []
   
   energy_input_to_electrolyzer=h2_ts.loc['Input Power [kWh]'].sum()
   average_uptime_hr=h2_tot.loc['Total Uptime [sec]'].mean()/3600
   
   elec_rated_h2_capacity_kgpy =h2_tot.loc['Cluster Rated H2 Production [kg/yr]'].sum()
   
   # cap_factor_sim=h2_tot.loc['Total H2 Production [kg]'].sum()/elec_rated_h2_capacity_kgpy

   hydrogen_hourly_production = h2_ts.loc['hydrogen_hourly_production'].sum()
   water_hourly_usage = h2_ts.loc['water_hourly_usage_kg'].sum()
   water_annual_usage = np.sum(water_hourly_usage)
   hourly_system_electrical_usage=h2_ts.loc['Power Consumed [kWh]'].sum()
   total_system_electrical_usage = np.sum(hourly_system_electrical_usage)
   avg_eff_perc=39.41*hydrogen_hourly_production/hourly_system_electrical_usage #np.nan_to_num(h2_ts.loc['electrolyzer_total_efficiency_perc'].mean())
   hourly_efficiency=np.nan_to_num(avg_eff_perc)
   tot_avg_eff=39.41/h2_tot.loc['Total kWh/kg'].mean()
   
   
   max_h2_pr_hr = h2_tot.loc['Cluster Rated H2 Production [kg/hr]'].sum()
   max_pwr_pr_hr = h2_tot.loc['Cluster Rated Power Consumed [kWh]'].sum()
   rated_kWh_pr_kg = h2_tot.loc['Stack Rated Efficiency [kWh/kg]'].mean()
   elec_rated_h2_capacity_kgpy =h2_tot.loc['Cluster Rated H2 Production [kg/yr]'].sum()
   cap_factor_sim = h2_tot.loc['PEM Capacity Factor (simulation)'].mean()
   # rated_kWh_pr_kg=h2_tot.loc['Stack Rated Power Consumed [kWh]'].values[0]/h2_tot.loc['Stack Rated H2 Production [kg/hr]'].values[0]
   # categories = ["Attribute","Simulation","Lifetime Estimate"]
   atrribute_desc = ["Efficiency [kWh/kg]","H2 Production [kg/hr]","Power Consumed [kWh]","Annual H2 Production [kg/year]"]
   sim = ["Capacity Factor","Active Time / Sim Time","Total Input Power [kWh]",\
      "Total H2 Produced [kg]",\
      "Average Efficiency [%-HHV]","Total Stack Off-Cycles","H2 Warm-Up Losses [kg]"]
   
   sim_specs = ['Sim: '+s for s in sim]
   attribute_specs = ['Rated BOL: '+s for s in atrribute_desc]
   # life_spec_desc = ['Life: ' + s for s in list(cluster_avg_df.index.values)]
   system_avg_life_eff_perc = 39.41/np.nanmean(h2_tot.loc['Average Efficiency [kWh/kg]'].values)
   system_avg_life_eff_kWh_pr_kg = np.nanmean(h2_tot.loc['Average Efficiency [kWh/kg]'].values)
   system_avg_life_capfac = np.nanmean(h2_tot.loc['Lifetime Capacity Factor [-]'].values)
   system_total_annual_h2_kg_pr_year = np.nansum(h2_tot.loc['Lifetime Average Annual Hydrogen Produced [kg]'].values)
   average_stack_life_hrs = np.nanmean(h2_tot.loc['Stack Life [hours]'].values)
   average_time_until_replacement = np.nanmean(h2_tot.loc['Time until replacement [hours]'].values)
   life_vals = [system_avg_life_capfac,system_total_annual_h2_kg_pr_year,average_stack_life_hrs,average_time_until_replacement,system_avg_life_eff_kWh_pr_kg,system_avg_life_eff_perc]
   life_desc = ["Life: Capacity Factor","Life: Annual H2 production [kg/year]","Stack Life [hrs]","Time Until Replacement [hrs]","Life: Efficiency [kWh/kg]","Life: Efficiency [%-HHV]"]
   
   attributes = [rated_kWh_pr_kg,max_h2_pr_hr,max_pwr_pr_hr,elec_rated_h2_capacity_kgpy]
   sim_performance = [h2_tot.loc['Total kWh/kg'].mean(),h2_tot.loc['Operational Time / Simulation Time (ratio)'].mean(),h2_tot.loc['Total Input Power [kWh]'].sum(),\
      h2_tot.loc['Total H2 Production [kg]'].sum(),\
      tot_avg_eff,h2_tot.loc['Total Off-Cycles'].sum(),h2_tot.loc['Warm-Up Losses on H2 Production'].sum()]
   new_H2_Results = dict(zip(attribute_specs,attributes))
   new_H2_Results.update(dict(zip(sim_specs,sim_performance)))
   new_H2_Results.update(dict(zip(life_desc,life_vals)))
   
   

   
   H2_Results = {'max_hydrogen_production [kg/hr]':
                  max_h2_pr_hr,
                  'hydrogen_annual_output':
                     system_total_annual_h2_kg_pr_year,
                  'cap_factor':
                  system_avg_life_capfac,
                  'cap_factor_sim':
                     cap_factor_sim ,
                  'hydrogen_hourly_production':
                     hydrogen_hourly_production,
                  'water_hourly_usage':
                  water_hourly_usage,
                  'water_annual_usage':
                  water_annual_usage,
                  'electrolyzer_avg_efficiency_percent':
                  system_avg_life_eff_perc,
                  # tot_avg_eff,
                  'electrolyzer_avg_efficiency_kWh_pr_kg':
                  system_avg_life_eff_kWh_pr_kg,
                  'total_electrical_consumption':
                  total_system_electrical_usage,
                  'electrolyzer_total_efficiency':
                  hourly_efficiency,
                  # 'time_between_replacement_per_stack':
                  # h2_tot.loc['Avg [hrs] until Replacement Per Stack'],
                  'avg_time_between_replacement':
                  average_time_until_replacement,
                  'avg_stack_life_hrs':
                  average_stack_life_hrs,
                  # h2_tot.loc['Avg [hrs] until Replacement Per Stack'].mean(),
                  'Rated kWh/kg-H2':rated_kWh_pr_kg,
                  'average_operational_time [hrs]':
                  average_uptime_hr,
                  'new_H2_Results':new_H2_Results
                  }

   
   if not debug_mode:
      h2_ts,h2_tot = clean_up_final_outputs(h2_tot,h2_ts)
  
   return H2_Results, h2_ts, h2_tot,energy_input_to_electrolyzer   
   