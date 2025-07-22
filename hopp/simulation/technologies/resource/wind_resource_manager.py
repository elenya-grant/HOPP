from typing import Union
from hopp.simulation.technologies.resource.wind_resource_types import (
    WTKSRW,
    BCHRRR,
    WTKLEDAlaska,
    WTKLEDConus,
    NOW23
)

class WindResource():
    _valid_datasets = ['windtoolkit','BC_HRRR','WTK_LED_Alaska','WTK_LED_CONUS','offshore','NOW23']
    _offshore_regions = ['ca','great-lakes','guam','gulf-of-mexico','hawaii','mid-atlantic','north-atlantic','nw-pacific','south-atlantic']
    _dataset_options = {
        "windtoolkit": WTKSRW,
        "BC_HRRR": BCHRRR,
        "WTK_LED_Alaska": WTKLEDAlaska,
        "WTK_LED_CONUS": WTKLEDConus,
        "offshore": NOW23,
        "NOW23": NOW23,
    }

    def __init__(
        self,
        hub_height: Union[float,int],
        wind_lat: float,
        wind_lon: float,
        wind_year: int,
        dataset_name: str = 'windtoolkit',
        wind_resource_obj: Union[object,dict,None] = None,
        **kwargs,
    ):

        dataset_name = dataset_name.strip()
        if wind_resource_obj is None or isinstance(wind_resource_obj,dict):
            if dataset_name not in self._valid_datasets:
                msg = (
                    f"{dataset_name} is not a valid wind resource dataset. "
                    f"Valid options include: {self._valid_datasets}"
                    )
                raise ValueError(msg)
            dataset = self._dataset_options[dataset_name]

            if wind_resource_obj is None:
                if dataset is NOW23 and 'offshore_region' not in kwargs:
                    msg = (
                        f'To use {dataset_name} dataset, please specify the offshore_region. ',
                        f'Offshore regions are: {self._offshore_regions}'
                    )
                    raise ValueError(msg)
            
            kwargs.update({"resource_data":wind_resource_obj})
            self.wind_resource = dataset(hub_height,wind_lat,wind_lon,wind_year,**kwargs)

            return
        # if any(v is wind_resource_obj for k,v in self._dataset_options.items()):
        if any(isinstance(wind_resource_obj,v) for k,v in self._dataset_options.items()):
            self.wind_resource = wind_resource_obj
            return

        msg = (
            "User input wind_resource_obj is not a valid wind resource datatype"
            )
        raise ValueError(msg)

    @property
    def data(self):
        return self.wind_resource._data
    
    @property
    def _data(self):
        return self.wind_resource._data

    def value(self, name: str, set_value=None):
        """Set or retrieve attribute of `hopp.simulation.technologies.wind.floris.Floris`.
            if set_value = None, then retrieve value; otherwise overwrite variable's value.
        
        Args:
            name (str): name of attribute to set or retrieve.
            set_value (Optional): value to set for variable `name`. 
                If `None`, then retrieve value. Defaults to None.
        """
        if set_value is not None:
            self.wind_resource.__setattr__(name, set_value)
        else:
            return self.wind_resource.__getattribute__(name)

# if __name__ == "__main__":
#     lat = 35.2018863
#     lon = -101.945027
#     year = 2012
#     height = 90
#     w_rsrc = WindResource(height,lat,lon,year,'windtoolkit',use_api = False,path_resource = '/Users/egrant/Documents/projects/HOPP/examples/weather')
#     w_rsrc.data