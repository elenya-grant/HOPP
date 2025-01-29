import os
import copy
from pathlib import Path

import pytest
from pytest import fixture
from shapely.geometry import Polygon
import numpy as np
from numpy.testing import assert_array_equal

from hopp.simulation.technologies.sites import SiteInfo, flatirons_site
from hopp import ROOT_DIR

from PySAM.ResourceTools import SRW_to_wind_data, SAM_CSV_to_solar_data

solar_resource_file = os.path.join(
    ROOT_DIR, "simulation", "resource_files", "solar", 
    "35.2018863_-101.945027_psmv3_60_2012.csv"
)
wind_resource_file = os.path.join(
    ROOT_DIR, "simulation", "resource_files", "wind", 
    "35.2018863_-101.945027_windtoolkit_2012_60min_80m_100m.srw"
)
grid_resource_file = os.path.join(
    ROOT_DIR, "simulation", "resource_files", "grid", 
    "pricing-data-2015-IronMtn-002_factors.csv"
)
kml_filepath = Path(__file__).absolute().parent / "layout_example.kml"


@fixture
def site():
    return SiteInfo(
        flatirons_site,
        solar_resource_file=solar_resource_file,
        wind_resource_file=wind_resource_file,
        grid_resource_file=grid_resource_file
    )


def test_site_init(site):
    """Site should initialize properly."""
    assert site is not None

    # data
    assert site.lat == flatirons_site["lat"]
    assert site.lon == flatirons_site["lon"]
    assert site.year == flatirons_site["year"]
    assert site.tz == flatirons_site["tz"]
    assert site.urdb_label == flatirons_site["urdb_label"]

    # resources
    assert site.solar_resource is not None
    assert site.wind_resource is not None
    assert site.elec_prices is not None

    # time periods
    assert site.n_timesteps == 8760
    assert site.n_periods_per_day == 24
    assert site.interval == 60
    assert_array_equal(site.capacity_hours, [False] * site.n_timesteps)
    assert_array_equal(site.desired_schedule, [])

    # polygon
    assert site.polygon is not None
    assert site.vertices is not None

    # unset
    assert site.kml_data is None


def test_site_init_kml_read():
    """Should initialize via kml file."""
    site = SiteInfo({"kml_file": kml_filepath}, solar_resource_file=solar_resource_file, wind_resource_file=wind_resource_file)

    assert site.kml_data is not None
    assert site.polygon is not None


def test_site_init_missing_coords():
    """Should fail if lat/lon missing."""
    data = copy.deepcopy(flatirons_site)
    del data["lat"]
    del data["lon"]

    with pytest.raises(ValueError):
        SiteInfo(data)

    data["lat"] = flatirons_site["lat"]

    # should still fail because lon is missing
    with pytest.raises(ValueError):
        SiteInfo(data)


def test_site_init_improper_schedule():
    """Should fail if the desired schedule mismatches the number of timesteps."""
    data = copy.deepcopy(flatirons_site)

    with pytest.raises(ValueError):
        SiteInfo(
            data, 
            solar_resource_file=solar_resource_file,
            wind_resource_file=wind_resource_file,
            grid_resource_file=grid_resource_file,
            desired_schedule=np.array([1])
        )


def test_site_init_no_wind():
    """Should initialize without pulling wind data."""
    data = copy.deepcopy(flatirons_site)

    site = SiteInfo(
        data, 
        solar_resource_file=solar_resource_file,
        wind_resource_file=wind_resource_file,
        grid_resource_file=grid_resource_file,
        wind=False
    )

    assert site.wind_resource is None

    
def test_site_init_no_solar():
    """Should initialize without pulling wind data."""
    data = copy.deepcopy(flatirons_site)

    site = SiteInfo(
        data, 
        solar_resource_file=solar_resource_file,
        wind_resource_file=wind_resource_file,
        grid_resource_file=grid_resource_file,
        solar=False
    )

    assert site.solar_resource is None


def test_site_kml_file_read():
    site_data = {'kml_file': kml_filepath}
    site = SiteInfo(site_data, solar_resource_file=solar_resource_file, wind_resource_file=wind_resource_file)
    assert np.array_equal(np.round(site.polygon.bounds), [ 681175., 4944970.,  686386., 4949064.])
    assert site.polygon.area * 3.86102e-7 == pytest.approx(2.3393, abs=0.01) # m2 to mi2


def test_site_kml_file_append():
    site_data = {'kml_file': kml_filepath}
    site = SiteInfo(site_data, solar_resource_file=solar_resource_file, wind_resource_file=wind_resource_file)

    x = site.polygon.centroid.x
    y = site.polygon.centroid.y
    turb_coords = [x - 500, y - 500]
    solar_region = Polygon(((x, y), (x, y + 5000), (x + 5000, y), (x + 5000, y + 5000)))

    filepath_new = Path(__file__).absolute().parent / "layout_example2.kml"
    site.kml_write(filepath_new, turb_coords, solar_region)
    assert filepath_new.exists()
    k, valid_region, lat, lon = SiteInfo.kml_read(kml_filepath)
    assert valid_region.area > 0
    os.remove(filepath_new)

def test_site_wind_resource_input_filename():
    data = copy.deepcopy(flatirons_site)
    wind_resource_data_dict = SRW_to_wind_data(wind_resource_file)
    site = SiteInfo(
        data, 
        hub_height = 90,
        wind = True,
        solar = False,
        wind_resource = wind_resource_data_dict
    )
    assert site.wind_resource.filename is None

def test_site_wind_resource_input_data_length():
    data = copy.deepcopy(flatirons_site)
    wind_resource_data_dict = SRW_to_wind_data(wind_resource_file)
    site = SiteInfo(
        data, 
        hub_height = 90,
        wind = True,
        solar = False,
        wind_resource = wind_resource_data_dict
    )
    assert len(site.wind_resource.data['data'])==8760

def test_site_wind_resource_input_data_format():
    data = copy.deepcopy(flatirons_site)
    wind_resource_data_dict = SRW_to_wind_data(wind_resource_file)
    site = SiteInfo(
        data, 
        hub_height = 90,
        wind = True,
        solar = False,
        wind_resource = wind_resource_data_dict
    )
    assert int(site.wind_resource.data['heights'][0])==80

def test_site_solar_resource_input_filename():
    data = copy.deepcopy(flatirons_site)
    solar_resource_data_dict = SAM_CSV_to_solar_data(solar_resource_file)
    site = SiteInfo(
        data, 
        wind = False,
        solar = True,
        solar_resource = solar_resource_data_dict
    )
    assert site.solar_resource.filename is None

def test_site_solar_resource_input_data_length():
    data = copy.deepcopy(flatirons_site)
    solar_resource_data_dict = SAM_CSV_to_solar_data(solar_resource_file)
    site = SiteInfo(
        data, 
        wind = False,
        solar = True,
        solar_resource = solar_resource_data_dict
    )
    assert len(site.solar_resource.data['dn'])==8760

def test_site_solar_resource_input_data_format():
    data = copy.deepcopy(flatirons_site)
    solar_resource_data_dict = SAM_CSV_to_solar_data(solar_resource_file)
    site = SiteInfo(
        data, 
        wind = False,
        solar = True,
        solar_resource = solar_resource_data_dict
    )
    assert site.solar_resource.data['tz']==-6

def test_different_resource_locations():
    tmp = copy.deepcopy(flatirons_site)
    data = {}
    data.update({'year':2012,'site_boundaries':tmp['site_boundaries']})
    resource_dict = {
    "wind_lat": 35.2018863,
    "wind_lon": -101.945027,
    "wind_year": 2012,
    "hub_height": 100,
    "solar_lat": 39.7555,
    "solar_lon": 105.2211,
    "solar_year": 2012,
    "lat": 34.0,
    "lon":-100.0,
    }
    data.update(resource_dict)
    site = SiteInfo(data,wind=True,solar=True)
    assert site.data['elev']==1879
    assert site.solar_resource.latitude == resource_dict["solar_lat"]
    assert site.wind_resource.latitude == resource_dict["wind_lat"]

def test_site_shape_for_rectangle():
    data = copy.deepcopy(flatirons_site)
    data.pop("site_boundaries")
    site_details = {"site_shape":"rectangle","site_area_km2":4,"aspect_ratio":2.0}
    data.update({"site_details":site_details})
    site = SiteInfo(data,wind=True,solar=True)

def test_site_shape_for_circle():
    data = copy.deepcopy(flatirons_site)
    data.pop("site_boundaries")
    site_details = {"site_shape":"circle","site_area_km2":4}
    data.update({"site_details":site_details})
    site = SiteInfo(data,wind=True,solar=True)

def test_site_shape_for_square():
    data = copy.deepcopy(flatirons_site)
    data.pop("site_boundaries")
    site_details = {"site_shape":"square","site_area_km2":4}
    data.update({"site_details":site_details})
    site = SiteInfo(data,wind=True,solar=True)

def test_site_shape_for_hexagon():
    data = copy.deepcopy(flatirons_site)
    data.pop("site_boundaries")
    site_details = {"site_shape":"hexagon","site_area_km2":4}
    data.update({"site_details":site_details})
    site = SiteInfo(data,wind=True,solar=True)
    
