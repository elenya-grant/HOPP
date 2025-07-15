from attrs import define, field
from typing import Union,Optional
from hopp.simulation.base import BaseClass
from hopp.type_dec import FromDictMixin
from hopp.utilities.validators import gt_zero, contains, range_val

from hopp.simulation.technologies.resource.wind_resource_types import (
    WTKSRW,
    BCHRRR,
    WTKLEDAlaska,
    WTKLEDConus,
    NOW23
)


@define
class WindResource(FromDictMixin):
    wind_lat: float
    wind_lon: float
    wind_year: int = field(converter = int)
    hub_height: Union[int,float] = field(validator=range_val(10.0,1000.0))
    
    
    data_hub_heights: Optional[list[int]]
    resource_data: Optional[dict]
    wtk_gid: Optional[int]
    api_params: Optional[dict]
    
    dataset: str = field(
        default = 'windtoolkit',
        validator=contains(['windtoolkit','BC_HRRR','WTK_LED_Alaska','WTK_LED_CONUS','offshore','NOW23']),
        converter=(str.strip)
        )


    

    def get_resource(self):
        dataset_options = {
                "windtoolkit": WTKSRW,
                "BC_HRRR": BCHRRR,
                "WTK_LED_Alaska": WTKLEDAlaska,
                "WTK_LED_CONUS": WTKLEDConus,
                "offshore": NOW23,
                "NOW23": NOW23,
            }
        
        offshore_regions = ['ca','great-lakes','guam','gulf-of-mexico','hawaii','mid-atlantic','north-atlantic','nw-pacific','south-atlantic']

        