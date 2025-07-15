from hopp.simulation.technologies.resource.wind_base import WindResourceBase
from hopp.utilities.keys import get_developer_nrel_gov_key, get_developer_nrel_gov_email
from hopp.tools.resource.pysam_wind_tools import combine_and_write_srw_files
from typing import Union, Optional
#https://github.com/NREL/HPC/blob/master/general/datasets/WIND/wtk_led_data.ipynb

class WTKSRW(WindResourceBase):
    _allowed_hub_height_meters: list[int] = [10, 40, 60, 80, 100, 120, 140, 160, 200]
    _year_range: tuple[int] = (2007,2014)
    _source_desc: str = 'windtoolkit'
    
    _url_base: str = 'https://developer.nrel.gov/api/wind-toolkit/v2/wind/wtk-srw-download'
    # _api_attributes: list[str] = []
    # _dataset_base_path: str = '/datasets/WIND/conus/v1.0.0/'

    def make_url(self,height):
        url = '{base}?year={year}&lat={lat}&lon={lon}&hubheight={hubheight}&api_key={api_key}&email={email}'.format(
            base=self._url_base, year=self.year, lat=self.latitude, lon=self.longitude, hubheight=height, api_key=get_developer_nrel_gov_key(), email=get_developer_nrel_gov_email()
        )
        return url
    
    def download_resource(self):
        success = False

        file_resource_heights = {}

        for height in self.data_hub_heights:
            filepath = self.make_default_filename(file_desc = f'{int(height)}m', file_type = 'srw')
            url = self.make_url()
            success = self.call_api(url, filename=filepath)
            file_resource_heights.update({int(height):filepath})
        
        if len(self.data_hub_heights)>1:
            combined_file_desc = "_".join(f"{int(height)}m" for height in self.data_hub_heights)
            self.filename = self.make_default_filename(combined_file_desc, file_type = 'srw')
            success = combine_and_write_srw_files(file_resource_heights,self.filename)
        else:
            self.filename = filepath
        
        if not success:
            raise ValueError('Unable to download wind data')

        return success

class BCHRRR(WindResourceBase):
    _allowed_hub_height_meters: list[int] = [10, 20, 40, 60, 80, 100, 120, 140, 160, 180, 200]
    _year_range: tuple[int] = (2015,2023)
    _source_desc: str = 'BC_HRRR'
    _url_base: str = 'https://developer.nrel.gov/api/wind-toolkit/v2/wind/wtk-bchrrr-v1-0-0-download.csv?'
    _api_attributes: list[str] = ["temperature","windspeed","winddirection","pressure_0m", "precipitationrate_0m"]
    _dataset_base_path: str = ''

    def get_dataset_filename(self):
        #TODO: update
        return f'filename_from_Dataset.h5'


class WTKLEDAlaska(WindResourceBase):
    _allowed_hub_height_meters: list[int] =  [10, 20, 40, 60, 80, 100, 120, 140, 160, 180, 200, 250, 300, 500, 1000]
    _year_range: tuple[int] = (2018,2020)
    _source_desc: str = 'WTK_LED_Alaksa'
    _url_base: str = 'https://developer.nrel.gov/api/wind-toolkit/v2/wind/wtk-alaska-v1-0-0-download.csv?'
    _api_attributes: list[str] = ["temperature","windspeed","winddirection","pressure_100m"]
    _dataset_base_path: str = ''

    def get_dataset_filename(self):
        #TODO: update
        return f'filename_from_Dataset.h5'


class WTKLEDConus(WindResourceBase):
    _allowed_hub_height_meters: list[int] =  [10, 20, 40, 60, 80, 100, 120, 140, 160, 180, 200, 250, 300, 500, 1000]
    _year_range: tuple[int] = (2019,2020)
    _source_desc: str = 'WTK_LED_CONUS'
    _url_base: str = 'https://developer.nrel.gov/api/wind-toolkit/v2/wind/wtk-led-conus-download.csv?'
    _api_attributes: list[str] = ["temperature","windspeed","winddirection","pressure_100m"]
    _dataset_base_path: str = '/datasets/WIND/conus/v2.0.0' #TODO: add
    
    def get_dataset_filename(self):
        #TODO: update
        return f'{self.year}/conus_{self.year}_heightm.h5'
    
    def extract_resource(self):
        #TODO: check if resource data is only output in 5min intervals!
        # Open file with rex WindX object
        
        wind_dict = {}
        for height in self.data_hub_heights:
            wtk_filepath = self.get_dataset_fpath()
            wtk_filepath = wtk_filepath.replace("heightm",f'{height}m')

            with WindX(wtk_filepath, hsds=False) as f:
                # get gid of location closest to given lat/lon coordinates and timezone offset
                if self.site_gid is None:
                    site_gid = f.lat_lon_gid((self.latitude, self.longitude))
                    self.site_gid = int(site_gid)

                self.data_tz = f.meta['timezone'].iloc[site_gid]
                self.site_tz = f.meta['timezone'].iloc[site_gid]
                self.data_lat = f.meta['latitude'].iloc[site_gid]
                self.data_lon = f.meta['longitude'].iloc[site_gid]


                # instantiate temp dictionary to hold each attributes dataset
                # loop through hub heights to download, capture datasets
                # NOTE: datasets are not auto shifted by timezone offset 
                # -> wrap extraction in SAMResource.roll_timeseries(input_array, timezone, #steps in an hour=1) to roll timezones
                
                #TODO: allow user to modify tz
                # wind_dict[f'temperature_{height}m'] = f['temperature_{height}m', :, site_gid]
                # NOTE: pressure datasets unit = Pa, convert to atm via division by 101325
                # wind_dict[f'pressure_{height}m'] = f['pressure_{height}m', :, site_gid]/101325
                wind_dict[f'speed_{height}m'] = f['windspeed_{height}m', :, site_gid]
                wind_dict[f'direction_{height}m'] = f['winddirection_{height}m', :, site_gid]
        return wind_dict

# class NOWCalifornia5Min(WindResourceBase):
#     #NOTE: This 
#     _allowed_hub_height_meters: list[int] = [10,40,60,80,100,120,140,160,180,200]
#     _year_range: tuple[int] = (2000,2020)
#     _source_desc: str = 'NOW_California5min'
#     _url_base: str = 'https://developer.nrel.gov/api/wind-toolkit/v2/wind/wtk-now23-california-v1-0-0-5min-download.csv?'

#     def check_resource_params(self):
#         self.n_timesteps = (60/5)*8760
#         self.api_params.update({'interval':'5'})
    # _api_attributes: list[str] = []
    # _dataset_base_path: str = ''

# class NOWCalifornia(WindResourceBase):
#     #NOTE: This 
#     _allowed_hub_height_meters: list[int] = [10,40,60,80,100,120,140,160,180,200]
#     _year_range: tuple[int] = (2000,2020)
#     _source_desc: str = 'NOW_California'
#     _url_base: str = 'https://developer.nrel.gov/api/wind-toolkit/v2/wind/offshore-ca-download.csv?'
    # _api_attributes: list[str] = []
    # _dataset_base_path: str = ''

class Template(WindResourceBase):
    _allowed_hub_height_meters: list[int] = [10,40,60,80,100,120,140,160,180,200]
    _year_range: tuple[int] = (2000,2020)
    _source_desc: str = '{file_output_id}'
    _url_base: str = 'https://developer.nrel.gov/api/wind-toolkit/v2/wind/{url_name}.csv?'
    # _api_attributes: list[str] = []
    # _dataset_base_path: str = ''
    def get_dataset_filename(self):
        return f'filename_from_Dataset.h5'



class NOW23(WindResourceBase):
    _allowed_hub_height_meters: list[int] = [10,40,60,80,100,120,140,160,180,200]
    _year_range: tuple[int] = (2000,2022) #(2000,2020)
    _offshore_locations = ['ca','great-lakes','guam','gulf-of-mexico','hawaii','mid-atlantic','north-atlantic','nw-pacific','south-atlantic']
    
    
    def __init__(
        self,
        hub_height: Union[float,int],
        lat: float,
        lon: float,
        year: int,
        offshore_location: str,
        data_hub_heights: Optional[list[int]] = [],
        resource_data: Optional[dict] = None,
        wtk_gid: Optional[int] = None,
        **kwargs,
    ):

        
        offshore_location = offshore_location.lower().strip()
        if offshore_location not in self._offshore_locations:
            raise ValueError(f'{offshore_location} is not a valid offshore_location. Options are {self._offshore_locations}')
        
        self._url_base = f'https://developer.nrel.gov/api/wind-toolkit/v2/wind/offshore-{offshore_location}-download.csv?'
        source_desc = ''.join(k.capitalize() for k in offshore_location.split("-"))
        self._source_desc = f'NOW23_{source_desc}'
        super().__init__(hub_height,lat,lon,year,data_hub_heights,resource_data,wtk_gid,**kwargs)

    def get_dataset_filename(self):
        #TODO: update
        return f'filename_from_Dataset.h5'

