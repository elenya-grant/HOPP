# tools to add floris to the hybrid simulation class
from attrs import define, field
from dataclasses import dataclass, asdict
import csv
from typing import TYPE_CHECKING, Tuple, List, Union
import numpy as np
import os
from floris import FlorisModel, TimeSeries
from floris.core import Core
from pathlib import Path
from hopp.utilities import load_yaml
from hopp.simulation.base import BaseClass
from hopp.simulation.technologies.sites import SiteInfo
from hopp.tools.design.wind.turbine_library_interface_tools import set_floris_turbine_specs
from hopp.tools.resource.wind_tools import calculate_air_density_for_elevation, parse_resource_data
# avoid circular dep
if TYPE_CHECKING:
    from hopp.simulation.technologies.wind.wind_plant import WindConfig
import hopp.tools.design.wind.floris_helper_tools as fi_tools
from hopp.tools.library import WIND_LIB
from hopp import ROOT_DIR
import matplotlib.pyplot as plt

@define
class Floris(BaseClass):
    site: SiteInfo = field()
    config: "WindConfig" = field()
    verbose: bool = field(default = False)

    _operational_losses: float = field(init=False)
    _timestep: Tuple[int, int] = field(init=False)
    annual_energy_pre_curtailment_ac: float = field(init=False)
    fi: FlorisModel = field(init=False)
    turbine_name: Union[str,List[str]] = field(init = False)

    def __attrs_post_init__(self):
        
        # 1) check that floris config is provided
        if self.config.floris_config is None:
            raise ValueError("A floris configuration must be provided")
        if self.config.timestep is None:
            raise ValueError("A timestep is required.")

        # 2) load floris config if needed
        if isinstance(self.config.floris_config,(str, Path)):
            # floris_config = Core.from_file(self.config.floris_config)
            floris_config = load_yaml(self.config.floris_config)
        else:
            floris_config = self.config.floris_config
        
        # 3) modify air density in floris config if needed
        if self.config.adjust_air_density_for_elevation and self.site.elev is not None:
            rho = calculate_air_density_for_elevation(self.site.elev)
            floris_config["flow_field"].update({"air_density":rho})
            # self.fi.set_(air_density = rho)
        
        # 4) update turbine in floris file if using turbine library
        if self.config.use_turbine_lib and self.config.turbine_name is not None:
            self.turbine_name = self.config.turbine_name
            floris_config = self.update_floris_config_from_turb_lib(floris_config)

        # 5) check for floris layout and check that floris layout is for the right number of turbines
        make_layout = self.check_for_layout(floris_config)
        if make_layout:
            if self.config.layout_mode == "basicgrid" and self.config.layout_params is not None:
                layout_params = self.config.layout_params
            else:
                layout_params = None
            rotor_diam = floris_config["farm"]["turbine_type"][0]["rotor_diameter"]
            x_pos, y_pos = fi_tools.make_default_layout(self.config.num_turbines,rotor_diam,layout_params,site = self.site)
            floris_config["farm"].update({"layout_x":x_pos,"layout_y":y_pos})
        
            # if not - then either print warning to logger and go with default layout
            # or raise warning
        # specify that hopp config has priority over floris config
        # hopp is highest level
        self.export_floris_files(floris_config)
        # 6) initialize floris model
        self.fi = FlorisModel(floris_config)
        turbine_names = list(self.fi.core.farm.turbine_power_thrust_tables.keys())
        if len(turbine_names)>1:
            self.turbine_name = turbine_names
        else:
            self.turbine_name = turbine_names[0]
        # self.fi = FlorisModel(floris_input_file)
        self._timestep = self.config.timestep
        self._operational_losses = self.config.operational_losses

        self.wind_resource_data = self.site.wind_resource.data
        self.speeds, self.wind_dirs = parse_resource_data(self.site.wind_resource)

        self.wind_farm_xCoordinates = self.fi.layout_x
        self.wind_farm_yCoordinates = self.fi.layout_y
        self.nTurbs = len(self.wind_farm_xCoordinates)
        self.turb_rating = self.config.turbine_rating_kw
        
        self.wind_turbine_rotor_diameter = self.fi.core.farm.rotor_diameters[0]
        if isinstance(turbine_names,list):
            system_capacity_kW = 0.0
            for ti,td in enumerate(self.fi.core.farm.turbine_definitions):
                system_capacity_kW += max(td["power_thrust_table"]["power"])
            self.system_capacity = system_capacity_kW

        else:
            self.system_capacity = self.nTurbs * self.turb_rating

        # turbine power curve (array of kW power outputs)
        self.wind_turbine_powercurve_powerout = []

        # time to simulate
        if len(self.config.timestep) > 0:
            self.start_idx = self.config.timestep[0]
            self.end_idx = self.config.timestep[1]
        else:
            self.start_idx = 0
            self.end_idx = 8759

        # results
        self.gen = []
        self.annual_energy = None
        self.capacity_factor = None

        self.initialize_from_floris()
    
    def update_floris_config_from_turb_lib(self,floris_config):
        wind_plant, turbine_dict = set_floris_turbine_specs(self.turbine_name,self)
        floris_config["farm"]["turbine_type"][0] = turbine_dict
        if "turbine_type" in floris_config["farm"]:
            if floris_config["farm"]["turbine_type"] is None:
                floris_config["farm"].update({"turbine_type":[turbine_dict]})
            elif isinstance(floris_config["farm"]["turbine_type"],list):
                if isinstance(floris_config["farm"]["turbine_type"][0],dict):
                    for key,val in turbine_dict.items():
                        if key in floris_config["farm"]["turbine_type"][0]:
                            if floris_config["farm"]["turbine_type"][0][key] is not None:
                                turbine_dict.update({key:floris_config["farm"]["turbine_type"][0][key]})
                else:
                    floris_config["farm"]["turbine_type"][0] = turbine_dict
            else:
                floris_config["farm"]["turbine_type"] = [turbine_dict]
        else:
            floris_config["farm"].update({"turbine_type":[turbine_dict]})

        # self.config.turbine_rating_kw = turbine_dict.pop("turbine_rating")
        self.turbine_rating = turbine_dict.pop("turbine_rating")
        self.config.rotor_diameter = turbine_dict["rotor_diameter"]
        self.config.hub_height = turbine_dict["hub_height"]
        return floris_config

    def initialize_from_floris(self):
        """
        Please populate all the wind farm parameters
        """
        self.nTurbs = len(self.fi.layout_x)
        if isinstance(self.turbine_name,str):
            self.wind_turbine_powercurve_powerout = list(self.fi.core.farm.turbine_power_thrust_tables[self.turbine_name]["power"])
        else:
            self.wind_turbine_powercurve_powerout = [1] * 30    # dummy for now
        

    def value(self, name: str, set_value=None):
        """
        if set_value = None, then retrieve value; otherwise overwrite variable's value
        """
        if set_value is not None:
            self.__setattr__(name, set_value)
        else:
            return self.__getattribute__(name)
    
    def set_floris_value(self,name,value):
        self.fi.set(**{name:value})
    
    def check_floris_turbine_library(self,turbine_name):
        from floris import turbine_library
        floris_turb_lib_files = os.listdir(turbine_library.__path__)
        floris_turb_lib_files = [f for f in floris_turb_lib_files if ".yaml" in f]
        if any(k.split(".yaml")[0]==turbine_name for k in floris_turb_lib_files):
            turb_filepath = os.path.join(turbine_library.__path__,f"{turbine_name}.yaml")
            turbine_model = load_yaml(turb_filepath)
        else:
            turbine_model = None
        return turbine_model

    def make_wind_rose(self,output_dir):
        
        time_series = TimeSeries(
            wind_directions=self.wind_dirs[self.start_idx:self.end_idx],
            wind_speeds=self.speeds[self.start_idx:self.end_idx],
            turbulence_intensities=self.fi.core.flow_field.turbulence_intensities[0]
        )
        vmin = 2.0
        vmax = 24.0
        dv = 2.0
        wind_rose = time_series.to_WindRose(wd_edges=np.arange(0, 360, 3.0), ws_edges=np.arange(vmin, vmax, dv))
        fig, ax = plt.subplots(subplot_kw={"polar": True})
 
        hub_ht = int(self.site.wind_resource.hub_height_meters)
        wind_rose.plot(ax=ax,legend_kwargs={"label": f"Wind Speed (m/s) at {hub_ht} m"})
        
        if output_dir is not None:
            fig_path = os.path.join(output_dir,f"wind_rose_{self.site.wind_resource.latitude}_{self.site.wind_resource.longitude}_{self.site.wind_resource.year}_{hub_ht}m.png")
            fig.savefig(fig_path)
            plt.close()

    def execute(self, project_life):
        
        if self.verbose:
            print('Simulating wind farm output in FLORIS...')

        # find generation of wind farm
        power_turbines = np.zeros((self.nTurbs, 8760))
        power_farm = np.zeros(8760)

        time_series = TimeSeries(
            wind_directions=self.wind_dirs[self.start_idx:self.end_idx],
            wind_speeds=self.speeds[self.start_idx:self.end_idx],
            turbulence_intensities=self.fi.core.flow_field.turbulence_intensities[0]
        )

        self.fi.set(wind_data=time_series)
        self.fi.run()

        power_turbines[:, self.start_idx:self.end_idx] = self.fi.get_turbine_powers().reshape((self.nTurbs, self.end_idx - self.start_idx))
        power_farm[self.start_idx:self.end_idx] = self.fi.get_farm_power().reshape((self.end_idx - self.start_idx))

        operational_efficiency = ((100 - self._operational_losses)/100)
        # Adding losses from PySAM defaults (excluding turbine and wake losses)
        self.gen = power_farm * operational_efficiency / 1000 # kW

        self.annual_energy = np.sum(self.gen) # kWh
        self.capacity_factor = np.sum(self.gen) / (8760 * self.system_capacity) * 100
        self.turb_powers = power_turbines * operational_efficiency / 1000 # kW
        self.turb_velocities = self.fi.turbine_average_velocities
        self.annual_energy_pre_curtailment_ac = np.sum(self.gen) # kWh

    def export(self):
        """
        Return all the floris system configuration in a dictionary for the financial model
        """
        config = {
            'system_capacity': self.system_capacity,
            'annual_energy': self.annual_energy,
        }
        return config

    def check_for_layout(self,floris_config):
        make_layout = True
        if "farm" in floris_config:
            if "layout_x" in floris_config["farm"] and "layout_y" in floris_config["farm"]:
                if len(floris_config["farm"]["layout_x"]) == self.config.num_turbines:
                    make_layout = False
                else:
                    if self.verbose:
                        layout_n_turbs = len(floris_config["farm"]["layout_x"])
                        print(f"provided layout has {layout_n_turbs} turbines but user-requests {self.config.num_turbines} turbines, making default layout for {self.config.num_turbines} turbines")
        return make_layout
    
    def check_valid_output_dir(self,output_dir):
        if output_dir is None:
            output_dir = str(WIND_LIB)
        if not os.path.isdir(output_dir):
            # check same root path as HOPP ROOT
            machine_root = "/" + "/".join(k for k in ROOT_DIR.parts[:3] if k!="/")
            if machine_root in output_dir:
                os.makedirs(output_dir)
            else:
                output_dir = str(WIND_LIB)
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)
        return output_dir

    def export_floris_files(self,floris_config):
        if self.config.turbine_management is not None:
            if "output_dir" in self.config.turbine_management:
                output_dir = self.check_valid_output_dir(self.config.turbine_management["output_dir"])
            else:
                output_dir = self.check_valid_output_dir(None)
            if "export_turbine_design" in self.config.turbine_management:
                if self.config.turbine_management["export_turbine_design"]:
                    turbine_dict = floris_config["farm"]["turbine_type"][0]
                    turbine_design_dir = os.path.join(output_dir,"turbine_designs")
                    self.check_valid_output_dir(turbine_design_dir)

                    fi_tools.write_turbine_to_floris_file(turbine_dict,turbine_design_dir)
            if "export_layout" in self.config.turbine_management:
                if self.config.turbine_management["export_layout"]:
                    layout_dir = os.path.join(output_dir,"wind_farm_layouts")
                    self.check_valid_output_dir(layout_dir)
                    # turbine_name = floris_config["farm"]["turbine_type"][0]["turbine_type"]
                    fi_tools.write_floris_layout_to_file(
                        floris_config["farm"]["layout_x"],
                        floris_config["farm"]["layout_y"],
                        layout_dir,
                        self.turbine_name)
