from abc import ABCMeta, abstractmethod
import os
import numpy as np
from pathlib import Path
from typing import Union, Optional
import urllib.parse
import re
import pandas as pd
import dill
from PySAM.ResourceTools import SRW_to_wind_data
from rex import WindX
from rex.sam_resource import SAMResource
from rex.resource_extraction import MultiYearWindX
from hopp import ROOT_DIR
from hopp.tools.resource.pysam_wind_tools import combine_wind_files, dataframe_to_wind_data, extract_site_specs_from_file
from hopp.utilities.keys import get_developer_nrel_gov_key, get_developer_nrel_gov_email
from hopp.simulation.technologies.resource.resource_base import Resource

#https://nrel.github.io/rex/index.html
# https://github.com/NREL/rex/blob/main/rex/sam_resource.py
#https://github.com/NREL/HPC/blob/master/general/datasets/WIND/wtk_led_data.ipynb
class WindResourceBase(Resource):
    _data_to_field_number = {'temperature': 1, 'pressure': 2, 'windspeed': 3, 'speed': 3,'winddirection': 4, 'direction': 4, 'precipitation_rate': 5}
    _allowed_hub_height_meters: list[int] = [10, 20, 40, 60, 80, 100, 120, 140, 160, 180, 200, 250, 300, 500, 1000]
    _year_range: tuple[int] = (2007,2023) #for catching error
    _source_desc: str = 'WindBase' #for output filenaming
    _resource_type: str = 'wind' #for user transparent
    
    _url_base: str = '' #for API calls
    _api_attributes: list[str] = ['temperature','windspeed','winddirection','pressure_100m'] #for API calls
    _dataset_base_path: str = '/datasets/WIND/conus/v1.0.0/' #for HPC access
    

    def __init__(
        self,
        hub_height: Union[float,int],
        lat: float,
        lon: float,
        year: int,
        data_hub_heights: Optional[list[int]] = [],
        resource_data: Optional[dict] = None,
        wtk_gid: Optional[int] = None,
        **kwargs,
    ):
        
        #: dictionary of preloaded and formatted wind resource data. Defaults to None.

        super().__init__(lat,lon,year,**kwargs)

        #check that hub-height is within reasonable range
        if hub_height<min(self._allowed_hub_height_meters) or hub_height>max(self._allowed_hub_height_meters):
            msg = (
                f'hub_height of {hub_height} is not within valid range. '
                f'Hub_height must be between {min(self._allowed_hub_height_meters)} and {max(self._allowed_hub_height_meters)}.'
                )
            raise ValueError(msg)
        
        # assign wind-specific attributes
        self.hub_height = hub_height
        # --- for HPC ---
        self.site_gid = wtk_gid
        self.data_lat = lat
        self.data_lat = lon

        self.data_tz = 0
        if len(data_hub_heights)>0:
            data_hub_heights = [hh for hh in data_hub_heights if hh in self._allowed_hub_height_meters]
        data_hub_heights += self.calculate_bounding_heights_from_allowed()
        self.data_hub_heights = list(set(data_hub_heights))

        # if resource_data is input as a dictionary then set_data 
        if resource_data is not None and isinstance(resource_data,dict):
            self.user_provided_data(resource_data)
            return 
        
        if str(self.filename)!='' and not self.use_api:
            self.user_provided_filepath(self.filename)
        
        if str(self.filename)=='':
            height_desc = "_".join(f"{h}m" for h in self.data_hub_heights)
            self.filename = self.make_default_filename(file_desc=height_desc)

        # check if theres an existing file
        if any(os.path.isfile(f"{str(self.filename).replace(Path(self.filename).suffix,ext)}") for ext in [".csv",".srw"]) and not self.use_api:
            filename = [f"{str(self.filename).replace(Path(self.filename).suffix,ext)}" for ext in ['.csv','.srw'] if os.path.isfile(f"{str(self.filename).replace(Path(self.filename).suffix,ext)}")][0]
            self.user_provided_filepath(filename)

        if 'heights' not in self._data and self.pull_on_init:
            self.pull_resource()

    def check_resource_params(self):
        return True

    def user_provided_data(self,resource_data:dict):
        required_keys = ['heights','fields','data']
        if all(k for k in required_keys in resource_data):
            self.data_hub_heights = list(set(resource_data['heights']))
            #TODO: add check that data_hub_heights make sense for hub-height
            n_timesteps = len(np.array(resource_data['data'])[:,0])
            if n_timesteps%8760 == 0:
                #TODO: this may throw an error if user inputs leap-year data
                self.api_params['interval'] = str(n_timesteps//8760)
                self.data = resource_data
                return
            
            msg = (
                f'Invalid data length. Data must be a multiple of 8760, data has {n_timesteps} entries'
            )
            raise ValueError(msg)
                
        msg = f'User provided data dictionary has incorrect keys, required keys are {required_keys}'
        raise ValueError(msg)

    def user_provided_filepath(self,resource_data_filepath:Union[Path,str]):
        resource_data_filepath = Path(resource_data_filepath)
        if os.path.isfile(str(resource_data_filepath)):
            self.path_resource = os.path.dirname(resource_data_filepath)
            self.filename = resource_data_filepath

            if resource_data_filepath.suffix == '.srw' or resource_data_filepath.suffix == '.csv':
                site_specs = extract_site_specs_from_file(resource_data_filepath)
                self.site_gid = site_specs['siteid']
                self.data_lat = site_specs['latitude']
                self.data_lon = site_specs['longitude']
                self.year = site_specs['year']

                data = combine_wind_files(resource_data_filepath,resource_heights = None)

                self.data_hub_heights = list(set(data['heights']))
                self.data = data
                return


            if resource_data_filepath.suffix == '.pkl':
                with open(resource_data_filepath,"rb") as f:
                    data = dill.load(f)
                if isinstance(data,dict):
                    self.user_provided_data(data)
                    return

                if isinstance(data,pd.DataFrame):
                    data = dataframe_to_wind_data(data)
                    self.data_hub_heights = list(set(data['heights']))
                    self.data = data
                    return
            if resource_data_filepath.suffix == '.h5':
                return

        raise FileNotFoundError(f'{resource_data_filepath} file does not exist')

    def calculate_bounding_heights_from_allowed(self):
        if any(float(hh) == float(self.hub_height_meters) for hh in self._allowed_hub_height_meters):
            return [int(self.hub_height_meters)]
        heights_lower = [hh for hh in self._allowed_hub_height_meters if hh/self.hub_height_meters<1]
        heights_upper = [hh for hh in self._allowed_hub_height_meters if hh/self.hub_height_meters>1]
        height_low = max(heights_lower) if len(heights_lower)>0 else min(self._allowed_hub_height_meters)
        height_high = min(heights_upper) if len(heights_upper)>0 else max(self._allowed_hub_height_meters)
        return [height_low,height_high]
    
    # def update_height(self, hub_height_meters):
    #     """Update hub-height and corresponding attributes. 
    #     Also updates ``file_resource_heights`` and ``filename``.

    #     Args:
    #         hub_height_meters (float): hub-height for wind resource data (meters)
    #     """
    #     self.hub_height_meters = hub_height_meters
    #     self.data_hub_heights = self.calculate_bounding_heights_from_allowed()

    
    def make_url(self,attributes = []):
        attributes += [a for a in self._api_attributes if len(re.findall('_([0-9]+)m',a))>0]
        for height in self.data_hub_heights:
            attributes += [f"{a}_{int(height)}m" for a in self._api_attributes if a not in attributes]

        attributes_str = ",".join(k for k in attributes)
        # input_data = {'attributes':attributes_str}da

        input_data = {}
        input_data.update(self.api_params)
        if 'attributes' in self.api_params:
            user_provided_attributes = self.api_params['attributes'].split(",")
            user_provided_attributes = [k.strip() for k in user_provided_attributes]
            attributes += [user_provided_attributes]
            attributes = list(set(attributes))
        
        attributes_str = ",".join(k for k in attributes)
        input_data.update({'attributes':attributes_str})
        
        # required_parameters = ['api_key','email','wkt','attributes','names','interval']
        # missing_parameters = [k for k in required_parameters if k not in self.api_params]
        input_data.setdefault('names',[str(self.year)])
        input_data.setdefault('wkt',f"POINT({self.longitude} {self.latitude})")
        if 'api_key' not in input_data:
            input_data.update({'api_key':get_developer_nrel_gov_key()})
        if 'email' not in input_data:
            input_data.update({'email':get_developer_nrel_gov_email()})
        
        url = self._url_base + urllib.parse.urlencode(input_data, True)
        return url

    def roll_timezone_for_data(self,tz_to:int,tz_from:int = 0):
        data = np.array(self.data['data']) #number of steps in an hour
        n_timesteps = 8760//len(data[:,0]) #number of time-steps in an hour
        tz_shift = tz_from + tz_to
        for i in range(len(self.data['fields'])):
            data[:,i] = SAMResource.roll_timeseries((data[:,i]), int(tz_shift), n_timesteps) 
        self.data_tz = tz_to
        self.data = data.tolist()
        return

    def download_resource(self):
        success = False

        url = self.make_url()
        
        success = self.call_api(url, filename=self.filename)
       
        if not success:
            raise ValueError('Unable to download wind data')

        return success
    
    def get_dataset_filename(self):
        return f'wtk_conus_{self.year}.h5'
        
    def get_dataset_fpath(self,dataset_filename: str = None):
        if dataset_filename is None:
            dataset_filename = self.get_dataset_filename()
            
        if self.filename is not None and os.path.isfile(self.filename) and Path(self.filename).suffix == '.h5':
            return self.filename
        
        if os.path.isdir(self.path_resource) and os.path.isfile((os.path.join(self.path_resource,dataset_filename))):
            return os.path.join(self.path_resource,dataset_filename)

        if os.path.isdir(self._dataset_base_path) and self._dataset_base_path!='':
            wtk_filepath = os.path.join(self._dataset_base_path,dataset_filename)
            if os.path.isfile(wtk_filepath):
                return wtk_filepath
            raise FileNotFoundError(f'{wtk_filepath} does not exist')
        
        raise FileNotFoundError(f'Can not find wind data file with filename {dataset_filename}')

    def extract_resource(self):
        # Open file with rex WindX object
        wtk_filepath = self.get_dataset_fpath()
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
            wind_dict = {}
            # loop through hub heights to download, capture datasets
            # NOTE: datasets are not auto shifted by timezone offset 
            # -> wrap extraction in SAMResource.roll_timeseries(input_array, timezone, #steps in an hour=1) to roll timezones
            
            #TODO: allow user to modify tz
            for height in self.data_hub_heights:
                wind_dict[f'temperature_{height}m'] = f['temperature_{height}m', :, site_gid]
                # NOTE: pressure datasets unit = Pa, convert to atm via division by 101325
                wind_dict[f'pressure_{height}m'] = f['pressure_{height}m', :, site_gid]/101325
                wind_dict[f'speed_{height}m'] = f['windspeed_{height}m', :, site_gid]
                wind_dict[f'direction_{height}m'] = f['winddirection_{height}m', :, site_gid]

        return wind_dict

    def pull_resource(self):
        success = False
        if self.data_source == 'API':
            success = self.download_resource()
            success = self.format_data()
        if self.data_source == 'HPC':
            wind_dict = self.extract_resource()
            success = self.format_extracted_data(wind_dict)

        return success
            
            
    def format_extracted_data(self,wind_dict):
        # round to desired precision and concatenate data into format needed for data dictionary
        # NOTE: Unsure if SAM/PySAM is sensitive to data types ie: floats with long precision vs to 2 or 3 decimals. 
        # If not sensitive, can remove following 8 lines of code to increase computational efficiency
        attribute_to_precision = {
            'temperature': 1,
            'pressure': 2,
            'speed': 3,
            'direction': 1,
        }
       
        # Remove data from feb29 on leap years
        if (self.year % 4) == 0:
            feb29 = np.arange(1416,1440)
            for key, value in wind_dict.items():
                wind_dict[key] = np.delete(value, feb29)

        
        # data_hub_heights = self.calculate_bounding_heights_from_allowed()
        resource_heights = []
        data_fields = []
        combined_data = []

        for height in self.data_hub_heights:
            for field_name,field_num in self._data_to_field_number.items():
                if f'{field_name}_{height}m' in wind_dict:
                    data_fields += [field_num]
                    resource_heights += [float(height)]
                    combined_data  += np.round((wind_dict[f'{field_name}_{height}m']), decimals=attribute_to_precision[field_name]).tolist()

        data = {
            'heights': resource_heights,
            'fields': data_fields,
            'data': combined_data,
            }

        # assign data
        self.data = data
        return True
        

    def format_data(self):
        """
        Format as 'wind_resource_data' dictionary for use in PySAM.
        """
        if self.data_source != 'API':
            raise ValueError('this function is only compatible with `API` as the data source')
        
        if not os.path.isfile(self.filename):
            raise FileNotFoundError(f"{self.filename} does not exist. Try `download_resource` first.")

        self.data = self.filename
        return True



    def extract_data_attributes(self,attribute_name:str,resource_height:Optional[Union[float,int]]):
        #TODO: finish this!
        valid_height = False
        if resource_height:
            valid_height = float(resource_height) in self.data['heights']
        else:
            resource_height = self.data['heigthts'][0]

        if attribute_name.lower() in self._data_to_field_number:
            pass
        else:
            msg = (
                f'{attribute_name} is not a valid wind resource attribute. Available options include '
                '`speed`,`direction`,`pressure`,`temperature`,`precipitation_rate`'
            )

    def roll_timeseries(self,tz_shift):
        utc_offset = timedelta(hours = pv_data['tz'])
        wind_df['utc_datetime'] = pd.to_datetime(wind_df[['year','month','day','hour','minute']])
        wind_df['datetime'] = wind_df['utc_datetime'] + utc_offset

        pass
    def resample_data(self,method='average'):
        
        pass

    @Resource.data.setter
    def data(self, data_info:dict):
        """
        Sets the wind resource data to a dictionary in SAM Wind format (see Pysam.ResourceTools.SRW_to_wind_data)
        """
        if isinstance(data_info,dict):
            self._data = data_info
            return
        if isinstance(data_info,(str,Path)):
            if '.srw' in data_info:
                self._data = SRW_to_wind_data(data_info)
                return
            if '.csv' in data_info:
                self._data = combine_wind_files(str(data_info),self.data_hub_heights)
                return
    @property
    def hub_height_meters(self):
        #NOTE: this only exists to prevent breaking code in pysam_wind_tools
        return self.hub_height

    @hub_height_meters.setter
    def hub_height_meters(self, hub_height):
        self.hub_height = hub_height
        self.data_hub_heights = self.calculate_bounding_heights_from_allowed()
       

# if __name__ == "__main__":
#     fpath = '/Users/egrant/Documents/projects/HOPP/hopp/simulation/resource_files/wind/42.2318_-83.9365_windtoolkit_2007_60min_60m.srw'
#     wind_data = SRW_to_wind_data(fpath)
#     p = WindResourceBase(90,50.0,50.0,1999,resource_data = wind_data,use_api = False,pull_on_init = False)
    # ,path_resource = ROOT_DIR/"elenya")
    # w = WindResourceBase(lat = 50, lon = 10, year = 1999, hub_height_meters=90)
    # class_attr_names = [a.name for a in w.__attrs_attrs__]

    []