# general imports
import os
import dill
# # yaml imports
import yaml
from yamlinclude import YamlIncludeConstructor
from pathlib import Path

PATH = Path(__file__).parent
YamlIncludeConstructor.add_to_loader_class(
    loader_class=yaml.FullLoader, base_dir=PATH / "./input/floris/"
)
YamlIncludeConstructor.add_to_loader_class(
    loader_class=yaml.FullLoader, base_dir=PATH / "./input/turbines/"
)

# HOPP imports
from greenheart.simulation.greenheart_simulation import (
    run_simulation,
    GreenHeartSimulationConfig,
)
from greenheart.tools.optimization.gc_run_greenheart import run_greenheart

# run the stuff
if __name__ == "__main__":
    # load inputs as needed
    turbine_model = "ATB2024_6MW_170RD_floris_turbine"
    filename_turbine_config = "./input/turbines/" + turbine_model + ".yaml"
    filename_floris_config = "./input/floris/floris_input_lbw_6MW.yaml"
    filename_hopp_config = "./input/plant/hopp_config_mn.yaml"
    # filename_greenheart_config = "./input/plant/greenheart_config_onshore_mn.yaml"
    policy_scenarios = [1,7]
    design_scenarios = [9,11]
    filename_greenheart_config = "./input/plant/greenheart_config_dri_mn.yaml"

    for incentive_num in policy_scenarios:
        for pdscenario in design_scenarios:
    
    # incentive_num = 1 #1 and 7
    # pdscenario = 11 #9 and 11

            output_dir = os.path.join(os.path.dirname(__file__),"10-25-2024","results-40percent_fullsize_CF1_-policy{}-design{}".format(incentive_num,pdscenario))
            # output_dir = os.path.join(os.path.dirname(__file__),"CF1_results-fullsize-policy{}-design{}".format(incentive_num,pdscenario))
            os.makedirs(output_dir,exist_ok=True)
            config = GreenHeartSimulationConfig(
                filename_hopp_config,
                filename_greenheart_config,
                filename_turbine_config,
                filename_floris_config,
                verbose=True,
                show_plots=False,
                save_plots=False,
                use_profast=True,
                post_processing=True,
                incentive_option=incentive_num,
                plant_design_scenario=pdscenario,
                output_level=8,
                output_dir=output_dir,
            )
            

            # for analysis
            res = run_simulation(config)
            attr_of_interest = ["electrolyzer_physics_results","profast_lcoh","capex_breakdown","opex_breakdown_annual","dri_capacity","dri_costs","dri_finance","greenheart_config","annual_energy_breakdown","hourly_energy_breakdown"]
            attr_of_interest +=["h2_storage_max_fill_rate_kg_hr","h2_storage_capacity_kg","hydrogen_storage_state_of_charge_kg"]
            print("output dir")
            print(output_dir)
            for thing in attr_of_interest:
                print("saving {}".format(thing))

                filename = os.path.join(output_dir,thing)
                data = res.__getattribute__(thing)
                with open(filename,"wb") as f:
                    dill.dump(data,f)

    # prob, config = run_greenheart(config, run_only=True)

    # for optimization
    # prob, config = run_greenheart(config, run_only=False)
    
    # lcoe = prob.get_val("lcoe", units="USD/(MW*h)")
    # lcoh = prob.get_val("lcoh", units="USD/kg")
    # lcos = prob.get_val("lcodri", units="USD/t")

    # print("LCOE: ", lcoe, "[$/MWh]")
    # print("LCOH: ", lcoh, "[$/kg]")
    # print("LCODRI: ", lcos, "[$/metric-tonne]")
    print("Done")
