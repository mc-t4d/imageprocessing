import ipywidgets as widgets
from ipywidgets import Layout
import ee
from mcimageprocessing.programmatic.APIs.EarthEngine import EarthEngineManager
import pkg_resources
import os
import rasterio
from rasterio.merge import merge

class WorldPop:
    """
    WorldPop class contains functions to download and process WorldPop data
    """

    def __init__(self):
        self.worldpop_agesex_bands = ['population', 'M_0', 'M_1', 'M_5', 'M_10', 'M_15', 'M_20', 'M_25', 'M_30', 'M_35',
                                      'M_40',
                                      'M_45', 'M_50', 'M_55', 'M_60', 'M_65', 'M_70', 'M_75', 'M_80', 'F_0',
                                      'F_1', 'F_5', 'F_10', 'F_15', 'F_20', 'F_25', 'F_30', 'F_35', 'F_40',
                                      'F_45', 'F_50', 'F_55', 'F_60', 'F_65', 'F_70', 'F_75', 'F_80']

        self.ee_auth_path = pkg_resources.resource_filename('mcimageprocessing', 'ee_auth_file.json')

        self.ee_instance = EarthEngineManager(authentication_file=self.ee_auth_path)


    def process_residential_population(self, input_file_path, output_file_path, age_band=None):
        """
        Process WorldPop residential population data to a single age band
        :param input_file_path: Path to the WorldPop residential population data
        :param output_file_path: Path to the output file
        :param age_band: Age band to process to. If None, the population data will be summed to a single band
        :return: Path to the output file
        """
        # Read the data


