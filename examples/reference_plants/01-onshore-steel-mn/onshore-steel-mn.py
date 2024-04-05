# general imports
import os

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

# run the stuff
if __name__ == "__main__":
    # load inputs as needed
    turbine_model = "lbw_6MW"
    filename_turbine_config = "./input/turbines/" + turbine_model + ".yaml"
    filename_floris_config = "./input/floris/floris_input_lbw_6MW.yaml"
    filename_hopp_config = "./input/plant/hopp_config_mn.yaml"
    filename_greenheart_config = "./input/plant/greenheart_config_onshore_mn.yaml"

    config = GreenHeartSimulationConfig(
        filename_hopp_config,
        filename_greenheart_config,
        filename_turbine_config,
        filename_floris_config,
        verbose=True,
        show_plots=False,
        save_plots=True,
        use_profast=True,
        post_processing=True,
        incentive_option=1,
        plant_design_scenario=9,
        output_level=7,
    )

    config.hopp_config["technologies"]["wind"]["fin_model"]["system_costs"]["om_fixed"][
        0
    ] = config.hopp_config["config"]["cost_info"]["wind_om_per_kw"]
    config.hopp_config["technologies"]["pv"]["fin_model"]["system_costs"]["om_fixed"][
        0
    ] = config.hopp_config["config"]["cost_info"]["pv_om_per_kw"]
    config.hopp_config["technologies"]["battery"]["fin_model"]["system_costs"][
        "om_batt_fixed_cost"
    ] = config.hopp_config["config"]["cost_info"]["battery_om_per_kw"]

    lcoe, lcoh, steel_finance, _ = run_simulation(config)

    print("LCOE: ", lcoe * 1e3, "[$/MWh]")
    print("LCOH: ", lcoh, "[$/kg]")
    print("LCOS: ", steel_finance.sol.get("price"), "[$/metric-tonne]")