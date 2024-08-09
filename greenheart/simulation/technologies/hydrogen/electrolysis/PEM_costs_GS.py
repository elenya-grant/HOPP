
import numpy as np
import numpy_financial as npf
from scipy.constants import liter,gallon
class PEM_Costs_GreenSteel:
    def __init__(self,atb_year: int, plant_life_yrs: int,cost_case = "Moderate",stack_replacement_cost_percent = 15, indirect_cost_fraction = 0.42, install_factor = 0.12, fixed_OM = 12.8, var_OM = 0.0013):
        self.years = [2022,2025,2030,2035]
        
        self.discount_year = 2020 #$2020/kW
        self.atb_year = atb_year
        self.plant_life_years = plant_life_yrs
        self.indirect_cost_fraction = indirect_cost_fraction
        self.install_factor = install_factor
        self.fixed_OM = fixed_OM #[$/kW-year]
        self.var_OM = var_OM #[$/kWh]
        self.stack_replacement_cost_ratio = stack_replacement_cost_percent/100

        advanced_uninstalled_capex = [1000,438,170,150] #HFTO Targets
        moderate_uninstalled_capex = [1000,566,340,279.8] #OCED Projections
        conservative_uninstalled_capex = [1000,801,476,420]
        if cost_case.lower()=="conservative" or cost_case.lower()=="high":
            self.uninstalled_capex = conservative_uninstalled_capex
        if cost_case.lower()=="moderate" or cost_case.lower()=="mid":
            self.uninstalled_capex = moderate_uninstalled_capex
        if cost_case.lower()=="advanced" or cost_case.lower()=="low":
            self.uninstalled_capex = advanced_uninstalled_capex
    
    def calc_overnight_capex(self,electrolyzer_size_MW):
        if not any(int(y)==self.atb_year for y in self.years):
            #check if this is limited to max
            coeff = np.polyfit(self.years,self.uninstalled_capex,1)
            capex_func = np.poly1d(coeff)
            direct_capex = capex_func(self.atb_year)
        else:
            direct_capex = [c for i,c in enumerate(self.uninstalled_capex) if self.years[i]==self.atb_year ]
            direct_capex = direct_capex[0]
        
        overnight_capex_usd_pr_kW = direct_capex*(1+self.indirect_cost_fraction)*(1+self.install_factor) #[$/kW]
        overnight_capex_usd = overnight_capex_usd_pr_kW*(electrolyzer_size_MW*1e3) #[$]
        return overnight_capex_usd_pr_kW,overnight_capex_usd

    def calc_variable_OM(self,energy_usage_kWh_pr_kg):
        if isinstance(energy_usage_kWh_pr_kg,list):
            annual_variable_OM_perkg = list(self.var_OM*np.array(energy_usage_kWh_pr_kg))
        else:
            annual_variable_OM_perkg = self.var_OM*energy_usage_kWh_pr_kg
        return annual_variable_OM_perkg

    def calc_fixed_OM(self,electrolyzer_size_MW):
        fixed_opex_USD_pr_year = self.fixed_OM*electrolyzer_size_MW*1e3
        return fixed_opex_USD_pr_year

    def calc_feedstock_usage(self,water_usage_liters_pr_kg):
        water_usage_gallons_pr_kg = water_usage_liters_pr_kg*(liter/gallon) #gallons water
        return water_usage_gallons_pr_kg
        
    def calc_stack_replacement_schedule(self,time_between_replacement_hours):
        stack_replacement_sched_percent_pr_year = np.zeros(self.plant_life_years)
        refturb_period = int(np.floor(time_between_replacement_hours/(24*365)))
        stack_replacement_sched_percent_pr_year[refturb_period:self.plant_life_years:refturb_period] = 1.0
        return stack_replacement_sched_percent_pr_year

    def calc_refurb_cost_schedule(self,stack_replacement_sched_percent_pr_year):
        stack_replacement_percent_capex_pr_year = self.stack_replacement_cost_ratio*stack_replacement_sched_percent_pr_year
        return list(stack_replacement_percent_capex_pr_year)
    
    
    def run(self,H2_Results):
        
        water_usage_liters_pr_kg = H2_Results["System Design"]["Feedstock Usage: Liters H2O/kg-H2"]
        n_stacks_pr_system = H2_Results["System Design"]["n_stacks/cluster"]*H2_Results["System Design"]["n_clusters/system"]
        electrolyzer_size_MW = H2_Results["System Design"]["System: BOL Rated Power [kW]"]/1e3
        _,overnight_capex_usd = self.calc_overnight_capex(electrolyzer_size_MW)
        if "Performance By Year" in H2_Results.keys():
            elec_cf = H2_Results["Performance By Year"]["Capacity Factor [-]"].to_list()
            energy_usage_kWh_pr_kg = H2_Results["Performance By Year"]["Annual Average Efficiency [kWh/kg]"].to_list()
            
            stack_replacement_sched_stacks_pr_year = np.array(H2_Results["Performance By Year"]["Refurbishment Schedule [stacks replaced/year]"].to_list())
            stack_replacement_sched_percent_pr_year = stack_replacement_sched_stacks_pr_year/n_stacks_pr_system
        else:
            elec_cf = H2_Results["Simulation Summary"]["Simulation Capacity Factor [-]"]
            time_between_replacement_hrs = ["Simulation Time Until Replacement [hrs]"]
            stack_replacement_sched_percent_pr_year = self.calc_stack_replacement_schedule(time_between_replacement_hrs)
            
            energy_usage_kWh_pr_kg = H2_Results["Simulation Summary"]["Total Power Usage [kW/sim]"]/H2_Results["Simulation Summary"]["Total Hydrogen Production [kg/sim]"]
        
        annual_variable_OM_perkg = self.calc_variable_OM(energy_usage_kWh_pr_kg)
        fixed_opex_USD_pr_year = self.calc_fixed_OM(electrolyzer_size_MW)
        stack_replacement_percent_capex_pr_year = self.calc_refurb_cost_schedule(stack_replacement_sched_percent_pr_year)
        water_feedstock_usage_gals_pr_kg = self.calc_feedstock_usage(water_usage_liters_pr_kg)
        
        electrolyzer_cost_results = {
        "electrolyzer_total_capital_cost": overnight_capex_usd,
        "electrolyzer_VOM_cost_per_kg_annual": annual_variable_OM_perkg,
        "electrolyzed_FOM_cost_annual":fixed_opex_USD_pr_year,
        "electrolyzer_refurb_schedule":stack_replacement_percent_capex_pr_year,
        "electrolyzer_water_feedstock_gals_pr_kg":water_feedstock_usage_gals_pr_kg,
    }
        return electrolyzer_cost_results

    def set_pf_params(self,bol_rated_h2_production_kg_pr_hr,elec_cf):
        #capacity is 
        daily_rated_capacity_kg_pr_day = bol_rated_h2_production_kg_pr_hr*24
        params = {"capacity":daily_rated_capacity_kg_pr_day,"long term utilization":elec_cf}
        return params

    def set_pf_capital_items(self,capex_usd,refurb_sched,depr_type,depr_period):
        keys = ["cost","depr_type","depr_period","refurb"]
        vals = [capex_usd,depr_type,depr_period,refurb_sched]
        return {"PEM Electrolysis Capital Cost":dict(zip(keys,vals))}

    def set_pf_fixed_costs(self,fixed_om_usd,profast_general_inflation=0.0):
        keys = ["usage","unit","cost","escalation"]
        vals = [1.0,"$/year",fixed_om_usd,profast_general_inflation]
        return {"PEM Electrolysis Fixed O&M":dict(zip(keys,vals))}
    
    def set_pf_variable_costs(self,vom_usd_pr_kg_pr_year,profast_general_inflation=0.0):
        keys = ["usage","unit","cost","escalation"]
        vals = [1.0,"$/kg",vom_usd_pr_kg_pr_year,profast_general_inflation]
        return {"PEM Electrolysis Variable O&M":dict(zip(keys,vals))}

    def set_pf_feedstock_costs(self,water_usage_gal_pr_kg,site_feedstock_region,profast_general_inflation=0.0):
        keys = ["usage","unit","cost","escalation"]
        vals = [water_usage_gal_pr_kg,"gal",site_feedstock_region,profast_general_inflation]
        return {"Water":dict(zip(keys,vals))}
        
    def create_years_of_operation(self,analysis_start_year,installation_period_months):
        operation_start_year = analysis_start_year + (installation_period_months/12)
        years_of_operation = np.arange(int(operation_start_year),int(operation_start_year+self.plant_life_years),1)
        year_keys = ['{}'.format(y) for y in years_of_operation]
        return year_keys

    def adjust_cost_for_dollar_year(self,component_cost_usd,cost_year:int,costing_general_inflation):
        periods = cost_year - self.discount_year
        adjusted_cost = -npf.fv(
            costing_general_inflation,
            periods,
            0.0,
            component_cost_usd,
        )
        return adjusted_cost

    def create_profast_dict(self,H2_Results,finance_config,adjust_costs_to_cost_year = True,site_feedstock_region = "US Average"):
        pf_dict = dict(zip(["params","capital_items","fixed_costs","feedstocks"],[None]*4))
        years_of_operation = self.create_years_of_operation(finance_config["analysis start year"],finance_config["installation months"])
        electrolyzer_cost_results = self.run(H2_Results)
        if adjust_costs_to_cost_year:
            result_cost_year = finance_config["cost_year"]
            cost_yr = finance_config["cost_year"]
            cst_gen_inf = finance_config["costing_general_inflation"]
            cost_keys = [c for c in list(electrolyzer_cost_results.keys()) if "cost" in c]
            for k in cost_keys:
                electrolyzer_cost_results[k] = self.adjust_cost_for_dollar_year(electrolyzer_cost_results[k],cost_yr,cst_gen_inf)
        else:
            result_cost_year = self.discount_year
        pf_gen_inf = finance_config["profast_general_inflation"]
        depr_type = finance_config["depreciation_method"]
        depr_period = finance_config["depreciation_period"]

        #NOTE: bol_rated_h2_production_kg_pr_hr is set assuming that a timestep of dt=3600 is used
        bol_rated_h2_production_kg_pr_hr = H2_Results["System Design"]["System: BOL Rated H2 Production [kg/dt]"]
        if "Performance By Year" in H2_Results.keys():
            elec_cf = dict(zip(years_of_operation,H2_Results["Performance By Year"]["Capacity Factor [-]"].to_list()))
        else:
            elec_cf = H2_Results["Simulation Summary"]["Simulation Capacity Factor [-]"]
        
        pf_params = self.set_pf_params(bol_rated_h2_production_kg_pr_hr,elec_cf)
        pf_dict["params"].update(pf_params)

        water_usage_gal_pr_kg = electrolyzer_cost_results["electrolyzer_water_feedstock_gals_pr_kg"]
        pf_water_feedstock = self.set_pf_feedstock_costs(water_usage_gal_pr_kg,site_feedstock_region,profast_general_inflation = pf_gen_inf)
        pf_dict["feedstocks"].update(pf_water_feedstock)

        fixed_om_usd = electrolyzer_cost_results["electrolyzed_FOM_cost_annual"]
        pf_fixed_om = self.set_pf_fixed_costs(fixed_om_usd,profast_general_inflation = pf_gen_inf)
        pf_dict["fixed_costs"].update(pf_fixed_om)

        if isinstance(electrolyzer_cost_results["electrolyzer_VOM_cost_per_kg_annual"],list):
            vom_usd_pr_kg_pr_year = dict(zip(years_of_operation,electrolyzer_cost_results["electrolyzer_VOM_cost_per_kg_annual"]))
        else:
            vom_usd_pr_kg_pr_year = electrolyzer_cost_results["electrolyzer_VOM_cost_per_kg_annual"]
        pf_vom = self.set_pf_variable_costs(vom_usd_pr_kg_pr_year,profast_general_inflation = pf_gen_inf)
        pf_dict["feedstocks"].update(pf_vom)
        
        refurb_sched = electrolyzer_cost_results["electrolyzer_refurb_schedule"]
        capex_usd = electrolyzer_cost_results["electrolyzer_total_capital_cost"]
        #TODO: FINISH FUNCTION BELOW
        pf_capital = self.set_pf_capital_items(capex_usd,refurb_sched,depr_type,depr_period)
        pf_dict["capital_items"].update(pf_capital)
        return pf_dict,result_cost_year