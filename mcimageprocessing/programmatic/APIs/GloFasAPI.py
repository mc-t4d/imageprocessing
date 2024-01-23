import cdsapi
import os

import datetime

import ipywidgets as widgets
from ipywidgets import DatePicker
from ipywidgets import VBox, HBox
import itertools
from mcimageprocessing import config_manager

class CDSAPI:
    def __init__(self):
        url = config_manager.config['KEYS']['GloFas']['url']
        key = config_manager.config['KEYS']['GloFas']['key']
        self.client = cdsapi.Client(url=url, key=key)

        self.glofas_dict = {
            "products": {
                # 'cems-glofas-seasonal': {
                #     "system_version": ['operational', 'version_3_1', 'version_2_2'],
                #     'hydrological_model': ['lisflood'],
                #     "variable": "river_discharge_in_the_last_24_hours",
                #     "leadtime_hour": list(range(24, 5161, 24)),
                #     "year": list(range(2019, datetime.date.today().year + 1)),
                #     "month": ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10",
                #               "11", "12"],
                #     # "day": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                #     # "area": [10.95, -90.95, -30.95, -29.95],
                #     "format": "grib"
                # },
                'cems-glofas-forecast': {
                    "system_version": ['operational', 'version_3_1', 'version_2_1'],
                    'hydrological_model': ['lisflood', 'htessel_lisflood'],
                    'product_type': [
                        'control_forecast', 'ensemble_perturbed_forecasts',
                    ],
                    "variable": "river_discharge_in_the_last_24_hours",
                    "leadtime_hour": list(range(24, 721, 24)),
                    "year": list(range(2020, datetime.date.today().year + 1)),
                    "month": ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10",
                              "11", "12"],
                    "day": list(range(24, 32)),
                    # "area": [10.95, -90.95, -30.95, -29.95],
                    "format": "grib"
                },
                # 'cems-glofas-reforecast': {
                #     "system_version": ['version_4_0', 'version_3_1', 'version_2_2'],
                #     'hydrological_model': ['lisflood', 'htessel_lisflood'],
                #     'product_type': [
                #         'control_forecast', 'ensemble_perturbed_forecasts',
                #     ],
                #     "leadtime_hour": list(range(24, 1105, 24)),
                #     "year": list(range(1999, datetime.date.today().year + 1)),
                #     "month": ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10",
                #               "11", "12"],
                #     "day": list(range(24, 32)),
                #     # "area": [10.95, -90.95, -30.95, -29.95],
                #     "format": "grib"
                # }
            }
        }

    def download_data(self, product_name, request_parameters, file_name):
        # Construct the file path
        day = request_parameters.get('day', '01')
        file_path = os.path.join(request_parameters['folder_location'], file_name)

        # Call the CDS API
        self.client.retrieve(
            product_name,
            {
                'variable': request_parameters['variable'],
                'format': request_parameters['format'],
                'system_version': request_parameters['system_version'],
                'hydrological_model': request_parameters['hydrological_model'],
                'product_type': request_parameters['product_type'],
                'year': request_parameters['year'],
                'day': day,
                'month': request_parameters['month'],
                'leadtime_hour': request_parameters['leadtime_hour'],
                'area': request_parameters['area'],
            },
            file_path
        )

        print(f"Downloaded data to {file_path}")
        return file_path

    def no_data_helper_function(self, glofas_product: str, glofas_params: dict):
        """
        Helper function to set no data values for a file
        :param file_path: Path to the file
        :param no_data_value: No data value to set
        :return: None
        """

        system_version_list = self.glofas_dict['products'][glofas_product]['system_version']
        hydrological_model_list = self.glofas_dict['products'][glofas_product]['hydrological_model']
        product_type_list = self.glofas_dict['products'][glofas_product].get('product_type', [None])

        all_combinations = list(itertools.product(system_version_list, hydrological_model_list, product_type_list))

        last_attempted_combination = (glofas_params['system_version'], glofas_params['hydrological_model'],
                                      glofas_params['product_type'] if glofas_params.get('product_type') else None)

        all_combinations.remove(last_attempted_combination)

        for comb in all_combinations:
            try:
                glofas_params['system_version'], glofas_params['hydrological_model'], glofas_params[
                    'product_type'] = comb
                file_path = self.download_glofas_data(bbox, glofas_params, index, distinct_values)
                self.process_and_clip_raster(file_path, geometry, glofas_params)
                return
            except Exception as e:
                print(e)
                if "no data is available within your requested subset" not in str(e):
                    break  # Exit the loop if a different error occurs

    def download_glofas_data(self, geometry, distinct_values, index):
        pass

