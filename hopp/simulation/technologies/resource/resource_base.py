from abc import ABCMeta, abstractmethod
import os
import json
import requests
import time
from pathlib import Path
from typing import Union, Optional
from hopp import ROOT_DIR
from attrs import define, field

from hopp.utilities.validators import range_val, contains
from hopp.utilities.utilities import check_create_folder
from hopp.type_dec import FromDictMixin

@define
class APIParameters(FromDictMixin):
    # generic api settings
    interval: Optional[int] = field(default =  60, validator = contains([5,15,30,60]))
    leap_year: Optional[str] = field(default = 'false') # if false, excludes leap year
    utc: Optional[str] = field(default = 'false') #: Pass true to retrieve data with timestamps in UTC, false to retrieve data with timestamps converted to local time of data point.
    name: Optional[str] = field(default = 'hybrid-systems')
    affiliation: Optional[str] = field(default = 'NREL')
    reason: Optional[str] = field(default = 'hybrid-analysis')
    # mailing_list: Optional[str] = field(default = 'true')
    api_key: Optional[str] = field(default=None)
    email: Optional[str] = field(default=None)
    # def __attrs_post_init__(self):
    #     if isinstance(self.leap_year,bool):
    #     if isinstance(self.utc,bool):

    def get_api_params(self,api_params = {}):
        d = self.as_dict()
        for k,v in d.items():
            if v is not None:
                api_params.setdefault(k,str(v))
        return api_params

class Resource(metaclass=ABCMeta):
    _year_range: tuple[int] = (1980, 2100)
    _source_desc: str = 'Base'
    _resource_type: str = 'none'
    """
    Class to manage resource data for a given lat & lon. If a resource file doesn't exist,
    it is downloaded and saved to 'resource_files' folder. The resource file is then read
    to the appropriate SAM resource data format.
    """
    def __init__(self, lat:float, lon:float, year:int, **kwargs):
        #: latitude corresponding to location for resource data in WGS84 CRS
        self.latitude = lat
        #: longitude corresponding to location for resource data in WGS84 CRS
        self.longitude = lon

        # check year
        if year not in range(*self._year_range):
            msg = (
                f'{year} is an invalid resource year. '
                f'Year must be in range {self._year_range}.'
            )
            raise ValueError(msg)
        
        #: year for resource data. 
        self.year = year

        # --- Default kwarg values --- 
        self.data_source: str = 'API' #Optional[str] = field(default="API", validator=contains(["API", "HPC"]), converter=(str.strip, str.upper))
        self.use_api: bool = False #API specific
        self.pull_on_init: bool = True
        self.api_params: Union[dict,APIParameters] = {} #API specific
        #: filepath to resource_files directory. Defaults to ROOT_DIR/"simulation"/"resource_files".
        self.path_resource: Union[str,Path] =  ROOT_DIR / "simulation" / "resource_files" / self._resource_type #Optional[Union[str, Path]] = field(default = ROOT_DIR / "simulation" / "resource_files")
        self.filename: Union[str,Path] = ''
        self.n_timesteps: int = 8760
        

        # check kwargs
        if any(k not in self.__dict__.keys() for k in kwargs.keys()):
            extra_args = [k for k in kwargs.keys() if k not in self.__dict__.keys()]
            raise AttributeError(
                f"The initialization for Resource was given extraneous inputs: {extra_args}"
            )
        
        kwargs.setdefault('path_resource',self.path_resource)
        kwargs['path_resource'] = Path(kwargs['path_resource'])
        if kwargs['path_resource'].parts[-1]!=self._resource_type:
            kwargs['path_resource'] = kwargs['path_resource'] / self._resource_type

        # update any passed in data
        self.__dict__.update(kwargs)

        # variables that can't be input
        self._data: dict = {}

        # check that data_source is valid
        self.data_source = self.data_source.strip().upper()
        if self.data_source not in ['API','HPC']:
            msg = (
                f"{self.data_source} is an invalid input for resource data_source, "
                "valid options include 'API' or 'HPC'."
            )
            raise ValueError(msg)
        
        # update API parameters if they'll be needed
        if self.data_source == "API":
            api_params = APIParameters()
            self.api_params = api_params.get_api_params(self.api_params)
            
            # if filename is input, update path_resource for consistency
            if len(str(self.filename)) > 0:
                filename_path = os.path.dirname(self.filename)
                if os.path.isdir(filename_path):
                    self.path_resource = Path(filename_path)
            
            #make folder for saving files if needed
            check_create_folder(str(self.path_resource))

        # check that n_timesteps matches interval
        n_timesteps_from_interval = int(8760 * 60/int(self.api_params['interval']))
        if n_timesteps_from_interval != int(self.n_timesteps):
            msg = (
                f"User input resource data interval as {self.api_params['interval']} minutes which would result in "
                f"{n_timesteps_from_interval} timesteps in a year but n_timesteps = {self.n_timesteps}. "
                "Please update n_timesteps to the number of intervals in a year."
            )
            raise ValueError(msg)
    
    # def get_resource_base_attributes(self):
    #     class_attr_names = [a.name for a in self.__attrs_attrs__]

    # @classmethod
    # def __attrs_init_subclass__(cls):
    #    print(f"Base has been subclassed by attrs {cls}.")

    def check_download_dir(self):
        """Creates directory for the resource file if it does not exist.
        """

        if not isinstance(self.filename,str):
            self.filename = str(self.filename)
        if not os.path.isdir(os.path.dirname(self.filename)):
            os.makedirs(os.path.dirname(self.filename))
    
    def make_default_filename(self, file_desc = '', file_type = 'csv'):
        if file_desc!='':
            file_name = f"{self.latitude}_{self.longitude}_{self._source_desc}_{self.year}_{self.api_params['interval']}min_{file_desc}.{file_type}"
        else:
            file_name = f"{self.latitude}_{self.longitude}_{self._source_desc}_{self.year}_{self.api_params['interval']}min.{file_type}"
        file_path = os.path.join(str(self.path_resource),file_name)
        return file_path

    @staticmethod
    def call_api(url, filename):
        """
        Args:
            url (str): The API endpoint to return data from
            filename (str): The filename where data should be written
        
        Returns:
            True if downloaded file successfully, False if encountered error in downloading
            
        """

        n_tries = 0
        success = False
        while n_tries < 5:

            try:
                r = requests.get(url)
                if r:
                    localfile = open(filename, mode='w+')
                    txt = r.text.replace("(Â°C)","(C)").replace("(Â°)","(deg)")
                    localfile.write(txt)
                    localfile.close()
                    if os.path.isfile(filename):
                        success = True
                        break
                elif r.status_code == 400 or r.status_code == 403:
                    print(r.url)
                    err = r.text
                    text_json = json.loads(r.text)
                    if 'errors' in text_json.keys():
                        err = text_json['errors']
                    raise requests.exceptions.HTTPError(err)
                elif r.status_code == 404:
                    print(filename)
                    raise requests.exceptions.HTTPError
                elif r.status_code == 429:
                    raise RuntimeError("Maximum API request rate exceeded!")
                else:
                    n_tries += 1 # Won't repeat endlessly (and exceed request limit) if API returns unexpected code
            except requests.exceptions.Timeout:
                time.sleep(0.2)
                n_tries += 1

        return success

    @abstractmethod
    def download_resource(self):
        """Download resource for given lat/lon"""
        
    @abstractmethod
    def make_url(self):
        """Make url for API calls"""

    @abstractmethod
    def extract_resource(self):
        """Download resource for given lat/lon"""

    @abstractmethod
    def pull_resource(self):
        """Download or Extract resource for given lat/lon then format"""
        # success = False
        # if self.data_source == 'API':
        #     success = self.download_resource()
        #     return success
        # if self.data_source == 'HPC':
        #     success = self.extract_resource()
        #     return success
        # raise ValueError('Invalid data_source')

    @abstractmethod
    def format_data(self):
        """Reads data from file and formats it for use in SAM"""

    @property
    def data(self):
        """Get data as dictionary formatted for SAM"""
        return self._data

    @data.setter
    @abstractmethod
    def data(self, data_dict):
        """Sets data from dictionary"""
