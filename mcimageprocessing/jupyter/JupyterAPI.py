import subprocess

import ee
import geopandas as gpd
import ipyfilechooser as fc
import ipywidgets as widgets
import localtileserver
import pandas as pd
import numpy as np
import pygrib
import json
from shapely.geometry import Point
from pyproj import Proj, transform
from IPython.display import HTML
from ipywidgets import Output
from ipyleaflet import GeoJSON
import ipyleaflet
from mcimageprocessing.jupyter.widget_creation_components.modis_flood_nrt import *
from mcimageprocessing.jupyter.widget_creation_components.worldpop import *
from mcimageprocessing.jupyter.widget_creation_components.global_flood_db import *
from shapely.geometry import shape
from shapely.geometry import MultiPolygon
from osgeo import gdal
import geojson
from rasterio.features import geometry_mask
from tqdm.notebook import tqdm as notebook_tqdm
from ipywidgets import VBox
from shapely.geometry import shape
import warnings
from IPython.display import display

# Define custom CSS
custom_css = """
<style>
/* Target labels of ipywidgets */
.widget-label {
    width: auto !important;
}
</style>

"""

boundary_dropdown = {'Admin 0': 'admin_0', 'Admin 1': 'admin_1', 'Admin 2': 'admin_2',
                     'Watersheds Level 1': 'watersheds_1',
                     'Watersheds Level 2': 'watersheds_2', 'Watersheds Level 3': 'watersheds_3',
                     'Watersheds Level 4': 'watersheds_4', 'Watersheds Level 5': 'watersheds_5',
                     'Watersheds Level 6': 'watersheds_6', 'Watersheds Level 7': 'watersheds_7',
                     'Watersheds Level 8': 'watersheds_8', 'Watersheds Level 9': 'watersheds_9',
                     'Watersheds Level 10': 'watersheds_10', 'Watersheds Level 11': 'watersheds_11',
                     'Watersheds Level 12': 'watersheds_12'}

boundary_definition_type = {'User Defined': 'user_defined', 'Predefined Boundaries': 'predefined',
                            'User Uploaded Data': 'user_uploaded'}

# Render the CSS in the notebook
HTML(custom_css)

warnings.filterwarnings('ignore', category=UserWarning, message="This was only*")

NODATA_VALUE = -9999


class OutputWidgetTqdm(notebook_tqdm):
    """
    OutputWidgetTqdm class

    This class is a subclass of the notebook_tqdm class. It provides a custom implementation for displaying progress using the tqdm library in Jupyter Notebook.

    Attributes:
    - output_widget: An output widget used to display the progress bar.

    Methods:
    - __init__(*args, **kwargs): Initializes the OutputWidgetTqdm instance. Accepts custom arguments and also the output_widget argument to extract the output widget.
    - display(*args, **kwargs): Overrides the display method of the superclass. Redirects the display to the output widget specified in the constructor.

    Note: This class requires the tqdm and ipywidgets libraries to be installed.

    Example usage:

    output_widget = OutputWidget()  # Instantiate the custom output widget
    widget_tqdm = OutputWidgetTqdm(output_widget=output_widget)  # Create an instance of OutputWidgetTqdm
    widget_tqdm.display()  # Display the progress bar in the output widget

    """

    def __init__(self, *args, **kwargs):
        # You can add custom arguments here if needed, or pass through to superclass
        self.output_widget = kwargs.pop('output_widget', None)  # Extract the output widget
        super().__init__(*args, **kwargs)

    def display(self, *args, **kwargs):
        # Override the display method to redirect to the output widget
        if self.output_widget:
            self.output_widget.clear_output(wait=True)
            with self.output_widget:
                display(self.container)


class JupyterAPI(geemap.Map):
    """

    """

    def __init__(self):
        super().__init__()

        self.setup_global_variables()

        self.create_widgets()

        self.setup_event_listeners()

        self.initialize_ui_state()

        for control in list(self.controls):
            if isinstance(control, ipyleaflet.WidgetControl):
                # Check for a specific property of the widget
                # For example, if the widget has a unique title, icon, or label
                if 'Search location/data' in str(control.widget) or 'wrench' in str(control):
                    self.remove_control(control)
                    continue

                    # self.update_final_output()

    def get_map_and_output(self):
        """

        :return: A tuple containing the map object `self` and the output attribute `self.out`.

        """
        return self, self.out

    def setup_global_variables(self):
        self.added_layers = {}
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

        self.gaul_dictionary = {'Afghanistan': {'GAUL': 1, 'ISO3': 'AFG', 'ISO2': 'AF'},
                                'Albania': {'GAUL': 3, 'ISO3': 'ALB', 'ISO2': 'AL'},
                                'Algeria': {'GAUL': 4, 'ISO3': 'DZA', 'ISO2': 'DZ'},
                                'American Samoa': {'GAUL': 5, 'ISO3': 'ASM', 'ISO2': 'AS'},
                                'Andorra': {'GAUL': 7, 'ISO3': 'AND', 'ISO2': 'AD'},
                                'Angola': {'GAUL': 8, 'ISO3': 'AGO', 'ISO2': 'AO'},
                                'Anguilla': {'GAUL': 9, 'ISO3': 'AIA', 'ISO2': 'AI'},
                                'Antarctica': {'GAUL': 10, 'ISO3': 'ATA', 'ISO2': 'AQ'},
                                'Antigua and Barbuda': {'GAUL': 11, 'ISO3': 'ATG', 'ISO2': 'AG'},
                                'Argentina': {'GAUL': 12, 'ISO3': 'ARG', 'ISO2': 'AR'},
                                'Armenia': {'GAUL': 13, 'ISO3': 'ARM', 'ISO2': 'AM'},
                                'Aruba': {'GAUL': 14, 'ISO3': 'ABW', 'ISO2': 'AW'},
                                'Australia': {'GAUL': 17, 'ISO3': 'AUS', 'ISO2': 'AU'},
                                'Austria': {'GAUL': 18, 'ISO3': 'AUT', 'ISO2': 'AT'},
                                'Azerbaijan': {'GAUL': 19, 'ISO3': 'AZE', 'ISO2': 'AZ'},
                                'Bahamas': {'GAUL': 20, 'ISO3': 'BHS', 'ISO2': 'BS'},
                                'Bahrain': {'GAUL': 21, 'ISO3': 'BHR', 'ISO2': 'BH'},
                                'Bangladesh': {'GAUL': 23, 'ISO3': 'BGD', 'ISO2': 'BD'},
                                'Barbados': {'GAUL': 24, 'ISO3': 'BRB', 'ISO2': 'BB'},
                                'Belarus': {'GAUL': 26, 'ISO3': 'BLR', 'ISO2': 'BY'},
                                'Belgium': {'GAUL': 27, 'ISO3': 'BEL', 'ISO2': 'BE'},
                                'Belize': {'GAUL': 28, 'ISO3': 'BLZ', 'ISO2': 'BZ'},
                                'Benin': {'GAUL': 29, 'ISO3': 'BEN', 'ISO2': 'BJ'},
                                'Bermuda': {'GAUL': 30, 'ISO3': 'BMU', 'ISO2': 'BM'},
                                'Bhutan': {'GAUL': 31, 'ISO3': 'BTN', 'ISO2': 'BT'},
                                'Bolivia': {'GAUL': 33, 'ISO3': 'BOL', 'ISO2': 'BO'},
                                'Bosnia and Herzegovina': {'GAUL': 34, 'ISO3': 'BIH', 'ISO2': 'BA'},
                                'Botswana': {'GAUL': 35, 'ISO3': 'BWA', 'ISO2': 'BW'},
                                'Bouvet Island': {'GAUL': 36, 'ISO3': 'BVT', 'ISO2': 'BV'},
                                'Brazil': {'GAUL': 37, 'ISO3': 'BRA', 'ISO2': 'BR'},
                                'British Indian Ocean Territory': {'GAUL': 38, 'ISO3': 'IOT', 'ISO2': 'IO'},
                                'British Virgin Islands': {'GAUL': 39, 'ISO3': 'VGB', 'ISO2': 'VG'},
                                'Brunei Darussalam': {'GAUL': 40, 'ISO3': 'BRN', 'ISO2': 'BN'},
                                'Bulgaria': {'GAUL': 41, 'ISO3': 'BGR', 'ISO2': 'BG'},
                                'Burkina Faso': {'GAUL': 42, 'ISO3': 'BFA', 'ISO2': 'BF'},
                                'Burundi': {'GAUL': 43, 'ISO3': 'BDI', 'ISO2': 'BI'},
                                'Cambodia': {'GAUL': 44, 'ISO3': 'KHM', 'ISO2': 'KH'},
                                'Cameroon': {'GAUL': 45, 'ISO3': 'CMR', 'ISO2': 'CM'},
                                'Canada': {'GAUL': 46, 'ISO3': 'CAN', 'ISO2': 'CA'},
                                'Cape Verde': {'GAUL': 47, 'ISO3': 'CPV', 'ISO2': 'CV'},
                                'Cayman Islands': {'GAUL': 48, 'ISO3': 'CYM', 'ISO2': 'KY'},
                                'Central African Republic': {'GAUL': 49, 'ISO3': 'CAF', 'ISO2': 'CF'},
                                'Chad': {'GAUL': 50, 'ISO3': 'TCD', 'ISO2': 'TD'},
                                'Chile': {'GAUL': 51, 'ISO3': 'CHL', 'ISO2': 'CL'},
                                'Christmas Island': {'GAUL': 54, 'ISO3': 'CXR', 'ISO2': 'CX'},
                                'Cocos (Keeling) Islands': {'GAUL': 56, 'ISO3': 'CCK', 'ISO2': 'CC'},
                                'Colombia': {'GAUL': 57, 'ISO3': 'COL', 'ISO2': 'CO'},
                                'Comoros': {'GAUL': 58, 'ISO3': 'COM', 'ISO2': 'KM'},
                                'Congo': {'GAUL': 59, 'ISO3': 'COG', 'ISO2': 'CG'},
                                'Cook Islands': {'GAUL': 60, 'ISO3': 'COK', 'ISO2': 'CK'},
                                'Costa Rica': {'GAUL': 61, 'ISO3': 'CRI', 'ISO2': 'CR'},
                                'Croatia': {'GAUL': 62, 'ISO3': 'HRV', 'ISO2': 'HR'},
                                'Cuba': {'GAUL': 63, 'ISO3': 'CUB', 'ISO2': 'CU'},
                                'Cyprus': {'GAUL': 64, 'ISO3': 'CYP', 'ISO2': 'CY'},
                                'Czech Republic': {'GAUL': 65, 'ISO3': 'CZE', 'ISO2': 'CZ'},
                                "Côte d'Ivoire": {'GAUL': 66, 'ISO3': 'CIV', 'ISO2': 'CI'},
                                "Dem People's Rep of Korea": {'GAUL': 67, 'ISO3': 'PRK', 'ISO2': 'KP'},
                                'Democratic Republic of the Congo': {'GAUL': 68, 'ISO3': 'COD', 'ISO2': 'CD'},
                                'Denmark': {'GAUL': 69, 'ISO3': 'DNK', 'ISO2': 'DK'},
                                'Djibouti': {'GAUL': 70, 'ISO3': 'DJI', 'ISO2': 'DJ'},
                                'Dominica': {'GAUL': 71, 'ISO3': 'DMA', 'ISO2': 'DM'},
                                'Dominican Republic': {'GAUL': 72, 'ISO3': 'DOM', 'ISO2': 'DO'},
                                'Ecuador': {'GAUL': 73, 'ISO3': 'ECU', 'ISO2': 'EC'},
                                'Egypt': {'GAUL': 40765, 'ISO3': 'EGY', 'ISO2': 'EG'},
                                'El Salvador': {'GAUL': 75, 'ISO3': 'SLV', 'ISO2': 'SV'},
                                'Equatorial Guinea': {'GAUL': 76, 'ISO3': 'GNQ', 'ISO2': 'GQ'},
                                'Eritrea': {'GAUL': 77, 'ISO3': 'ERI', 'ISO2': 'ER'},
                                'Estonia': {'GAUL': 78, 'ISO3': 'EST', 'ISO2': 'EE'},
                                'Ethiopia': {'GAUL': 79, 'ISO3': 'ETH', 'ISO2': 'ET'},
                                'Falkland Islands (Malvinas)': {'GAUL': 81, 'ISO3': 'FLK', 'ISO2': 'FK'},
                                'Faroe Islands': {'GAUL': 82, 'ISO3': 'FRO', 'ISO2': 'FO'},
                                'Fiji': {'GAUL': 83, 'ISO3': 'FJI', 'ISO2': 'FJ'},
                                'Finland': {'GAUL': 84, 'ISO3': 'FIN', 'ISO2': 'FI'},
                                'France': {'GAUL': 85, 'ISO3': 'FRA', 'ISO2': 'FR'},
                                'French Guiana': {'GAUL': 86, 'ISO3': 'GUF', 'ISO2': 'GF'},
                                'French Polynesia': {'GAUL': 87, 'ISO3': 'PYF', 'ISO2': 'PF'},
                                'French Southern and Antarctic Territories': {'GAUL': 88, 'ISO3': 'ATF', 'ISO2': 'TF'},
                                'Gabon': {'GAUL': 89, 'ISO3': 'GAB', 'ISO2': 'GA'},
                                'Gambia': {'GAUL': 90, 'ISO3': 'GMB', 'ISO2': 'GM'},
                                'Georgia': {'GAUL': 92, 'ISO3': 'GEO', 'ISO2': 'GE'},
                                'Germany': {'GAUL': 93, 'ISO3': 'DEU', 'ISO2': 'DE'},
                                'Ghana': {'GAUL': 94, 'ISO3': 'GHA', 'ISO2': 'GH'},
                                'Gibraltar': {'GAUL': 95, 'ISO3': 'GIB', 'ISO2': 'GI'},
                                'Greece': {'GAUL': 97, 'ISO3': 'GRC', 'ISO2': 'GR'},
                                'Greenland': {'GAUL': 98, 'ISO3': 'GRL', 'ISO2': 'GL'},
                                'Grenada': {'GAUL': 99, 'ISO3': 'GRD', 'ISO2': 'GD'},
                                'Guadeloupe': {'GAUL': 100, 'ISO3': 'GLP', 'ISO2': 'GP'},
                                'Guam': {'GAUL': 101, 'ISO3': 'GUM', 'ISO2': 'GU'},
                                'Guatemala': {'GAUL': 103, 'ISO3': 'GTM', 'ISO2': 'GT'},
                                'Guernsey': {'GAUL': 104, 'ISO3': 'GGY', 'ISO2': 'GG'},
                                'Guinea': {'GAUL': 106, 'ISO3': 'GIN', 'ISO2': 'GN'},
                                'Guinea-Bissau': {'GAUL': 105, 'ISO3': 'GNB', 'ISO2': 'GW'},
                                'Guyana': {'GAUL': 107, 'ISO3': 'GUY', 'ISO2': 'GY'},
                                'Haiti': {'GAUL': 108, 'ISO3': 'HTI', 'ISO2': 'HT'},
                                'Heard Island and McDonald Islands': {'GAUL': 109, 'ISO3': 'HMD', 'ISO2': 'HM'},
                                'Holy See': {'GAUL': 110, 'ISO3': 'VAT', 'ISO2': 'VA'},
                                'Honduras': {'GAUL': 111, 'ISO3': 'HND', 'ISO2': 'HN'},
                                'Hong Kong': {'GAUL': 33364, 'ISO3': 'HKG', 'ISO2': 'HK'},
                                'Hungary': {'GAUL': 113, 'ISO3': 'HUN', 'ISO2': 'HU'},
                                'Iceland': {'GAUL': 114, 'ISO3': 'ISL', 'ISO2': 'IS'},
                                'India': {'GAUL': 115, 'ISO3': 'IND', 'ISO2': 'IN'},
                                'Indonesia': {'GAUL': 116, 'ISO3': 'IDN', 'ISO2': 'ID'},
                                'Iran  (Islamic Republic of)': {'GAUL': 117, 'ISO3': 'IRN', 'ISO2': 'IR'},
                                'Iraq': {'GAUL': 118, 'ISO3': 'IRQ', 'ISO2': 'IQ'},
                                'Ireland': {'GAUL': 119, 'ISO3': 'IRL', 'ISO2': 'IE'},
                                'Isle of Man': {'GAUL': 120, 'ISO3': 'IMN', 'ISO2': 'IM'},
                                'Israel': {'GAUL': 121, 'ISO3': 'ISR', 'ISO2': 'IL'},
                                'Italy': {'GAUL': 122, 'ISO3': 'ITA', 'ISO2': 'IT'},
                                'Jamaica': {'GAUL': 123, 'ISO3': 'JAM', 'ISO2': 'JM'},
                                'Japan': {'GAUL': 126, 'ISO3': 'JPN', 'ISO2': 'JP'},
                                'Jersey': {'GAUL': 128, 'ISO3': 'JEY', 'ISO2': 'JE'},
                                'Jordan': {'GAUL': 130, 'ISO3': 'JOR', 'ISO2': 'JO'},
                                'Kazakhstan': {'GAUL': 132, 'ISO3': 'KAZ', 'ISO2': 'KZ'},
                                'Kenya': {'GAUL': 133, 'ISO3': 'KEN', 'ISO2': 'KE'},
                                'Kiribati': {'GAUL': 135, 'ISO3': 'KIR', 'ISO2': 'KI'},
                                'Kuwait': {'GAUL': 137, 'ISO3': 'KWT', 'ISO2': 'KW'},
                                'Kyrgyzstan': {'GAUL': 138, 'ISO3': 'KGZ', 'ISO2': 'KG'},
                                "Lao People's Democratic Republic": {'GAUL': 139, 'ISO3': 'LAO', 'ISO2': 'LA'},
                                'Latvia': {'GAUL': 140, 'ISO3': 'LVA', 'ISO2': 'LV'},
                                'Lebanon': {'GAUL': 141, 'ISO3': 'LBN', 'ISO2': 'LB'},
                                'Lesotho': {'GAUL': 142, 'ISO3': 'LSO', 'ISO2': 'LS'},
                                'Liberia': {'GAUL': 144, 'ISO3': 'LBR', 'ISO2': 'LR'},
                                'Libya': {'GAUL': 145, 'ISO3': 'LBY', 'ISO2': 'LY'},
                                'Liechtenstein': {'GAUL': 146, 'ISO3': 'LIE', 'ISO2': 'LI'},
                                'Lithuania': {'GAUL': 147, 'ISO3': 'LTU', 'ISO2': 'LT'},
                                'Luxembourg': {'GAUL': 148, 'ISO3': 'LUX', 'ISO2': 'LU'},
                                'Macau': {'GAUL': 149, 'ISO3': 'MAC', 'ISO2': 'MO'},
                                'Madagascar': {'GAUL': 150, 'ISO3': 'MDG', 'ISO2': 'MG'},
                                'Malawi': {'GAUL': 152, 'ISO3': 'MWI', 'ISO2': 'MW'},
                                'Malaysia': {'GAUL': 153, 'ISO3': 'MYS', 'ISO2': 'MY'},
                                'Maldives': {'GAUL': 154, 'ISO3': 'MDV', 'ISO2': 'MV'},
                                'Mali': {'GAUL': 155, 'ISO3': 'MLI', 'ISO2': 'ML'},
                                'Malta': {'GAUL': 156, 'ISO3': 'MLT', 'ISO2': 'MT'},
                                'Marshall Islands': {'GAUL': 157, 'ISO3': 'MHL', 'ISO2': 'MH'},
                                'Martinique': {'GAUL': 158, 'ISO3': 'MTQ', 'ISO2': 'MQ'},
                                'Mauritania': {'GAUL': 159, 'ISO3': 'MRT', 'ISO2': 'MR'},
                                'Mauritius': {'GAUL': 160, 'ISO3': 'MUS', 'ISO2': 'MU'},
                                'Mayotte': {'GAUL': 161, 'ISO3': 'MYT', 'ISO2': 'YT'},
                                'Mexico': {'GAUL': 162, 'ISO3': 'MEX', 'ISO2': 'MX'},
                                'Micronesia (Federated States of)': {'GAUL': 163, 'ISO3': 'FSM', 'ISO2': 'FM'},
                                'Moldova, Republic of': {'GAUL': 165, 'ISO3': 'MDA', 'ISO2': 'MD'},
                                'Monaco': {'GAUL': 166, 'ISO3': 'MCO', 'ISO2': 'MC'},
                                'Mongolia': {'GAUL': 167, 'ISO3': 'MNG', 'ISO2': 'MN'},
                                'Montenegro': {'GAUL': 2647, 'ISO3': 'MNE', 'ISO2': 'ME'},
                                'Montserrat': {'GAUL': 168, 'ISO3': 'MSR', 'ISO2': 'MS'},
                                'Morocco': {'GAUL': 169, 'ISO3': 'MAR', 'ISO2': 'MA'},
                                'Mozambique': {'GAUL': 170, 'ISO3': 'MOZ', 'ISO2': 'MZ'},
                                'Myanmar': {'GAUL': 171, 'ISO3': 'MMR', 'ISO2': 'MM'},
                                'Namibia': {'GAUL': 172, 'ISO3': 'NAM', 'ISO2': None},
                                'Nauru': {'GAUL': 173, 'ISO3': 'NRU', 'ISO2': 'NR'},
                                'Nepal': {'GAUL': 175, 'ISO3': 'NPL', 'ISO2': 'NP'},
                                'Netherlands': {'GAUL': 177, 'ISO3': 'NLD', 'ISO2': 'NL'},
                                'Netherlands Antilles': {'GAUL': 176, 'ISO3': 'BES', 'ISO2': 'BQ'},
                                'New Caledonia': {'GAUL': 178, 'ISO3': 'NCL', 'ISO2': 'NC'},
                                'New Zealand': {'GAUL': 179, 'ISO3': 'NZL', 'ISO2': 'NZ'},
                                'Nicaragua': {'GAUL': 180, 'ISO3': 'NIC', 'ISO2': 'NI'},
                                'Niger': {'GAUL': 181, 'ISO3': 'NER', 'ISO2': 'NE'},
                                'Nigeria': {'GAUL': 182, 'ISO3': 'NGA', 'ISO2': 'NG'},
                                'Niue': {'GAUL': 183, 'ISO3': 'NIU', 'ISO2': 'NU'},
                                'Norfolk Island': {'GAUL': 184, 'ISO3': 'NFK', 'ISO2': 'NF'},
                                'Northern Mariana Islands': {'GAUL': 185, 'ISO3': 'MNP', 'ISO2': 'MP'},
                                'Norway': {'GAUL': 186, 'ISO3': 'NOR', 'ISO2': 'NO'},
                                'Oman': {'GAUL': 187, 'ISO3': 'OMN', 'ISO2': 'OM'},
                                'Pakistan': {'GAUL': 188, 'ISO3': 'PAK', 'ISO2': 'PK'},
                                'Palau': {'GAUL': 189, 'ISO3': 'PLW', 'ISO2': 'PW'},
                                'Panama': {'GAUL': 191, 'ISO3': 'PAN', 'ISO2': 'PA'},
                                'Papua New Guinea': {'GAUL': 192, 'ISO3': 'PNG', 'ISO2': 'PG'},
                                'Paraguay': {'GAUL': 194, 'ISO3': 'PRY', 'ISO2': 'PY'},
                                'Peru': {'GAUL': 195, 'ISO3': 'PER', 'ISO2': 'PE'},
                                'Philippines': {'GAUL': 196, 'ISO3': 'PHL', 'ISO2': 'PH'},
                                'Pitcairn': {'GAUL': 197, 'ISO3': 'PCN', 'ISO2': 'PN'},
                                'Poland': {'GAUL': 198, 'ISO3': 'POL', 'ISO2': 'PL'},
                                'Portugal': {'GAUL': 199, 'ISO3': 'PRT', 'ISO2': 'PT'},
                                'Puerto Rico': {'GAUL': 200, 'ISO3': 'PRI', 'ISO2': 'PR'},
                                'Qatar': {'GAUL': 201, 'ISO3': 'QAT', 'ISO2': 'QA'},
                                'Republic of Korea': {'GAUL': 202, 'ISO3': 'KOR', 'ISO2': 'KR'},
                                'Romania': {'GAUL': 203, 'ISO3': 'ROU', 'ISO2': 'RO'},
                                'Russian Federation': {'GAUL': 204, 'ISO3': 'RUS', 'ISO2': 'RU'},
                                'Rwanda': {'GAUL': 205, 'ISO3': 'RWA', 'ISO2': 'RW'},
                                'Réunion': {'GAUL': 206, 'ISO3': 'REU', 'ISO2': 'RE'},
                                'Saint Helena': {'GAUL': 207, 'ISO3': 'SHN', 'ISO2': 'SH'},
                                'Saint Kitts and Nevis': {'GAUL': 208, 'ISO3': 'KNA', 'ISO2': 'KN'},
                                'Saint Lucia': {'GAUL': 209, 'ISO3': 'LCA', 'ISO2': 'LC'},
                                'Saint Pierre et Miquelon': {'GAUL': 210, 'ISO3': 'SPM', 'ISO2': 'PM'},
                                'Saint Vincent and the Grenadines': {'GAUL': 211, 'ISO3': 'VCT', 'ISO2': 'VC'},
                                'Samoa': {'GAUL': 212, 'ISO3': 'WSM', 'ISO2': 'WS'},
                                'San Marino': {'GAUL': 213, 'ISO3': 'SMR', 'ISO2': 'SM'},
                                'Sao Tome and Principe': {'GAUL': 214, 'ISO3': 'STP', 'ISO2': 'ST'},
                                'Saudi Arabia': {'GAUL': 215, 'ISO3': 'SAU', 'ISO2': 'SA'},
                                'Senegal': {'GAUL': 217, 'ISO3': 'SEN', 'ISO2': 'SN'},
                                'Serbia': {'GAUL': 2648, 'ISO3': 'SRB', 'ISO2': 'RS'},
                                'Seychelles': {'GAUL': 220, 'ISO3': 'SYC', 'ISO2': 'SC'},
                                'Sierra Leone': {'GAUL': 221, 'ISO3': 'SLE', 'ISO2': 'SL'},
                                'Singapore': {'GAUL': 222, 'ISO3': 'SGP', 'ISO2': 'SG'},
                                'Slovakia': {'GAUL': 223, 'ISO3': 'SVK', 'ISO2': 'SK'},
                                'Slovenia': {'GAUL': 224, 'ISO3': 'SVN', 'ISO2': 'SI'},
                                'Solomon Islands': {'GAUL': 225, 'ISO3': 'SLB', 'ISO2': 'SB'},
                                'Somalia': {'GAUL': 226, 'ISO3': 'SOM', 'ISO2': 'SO'},
                                'South Africa': {'GAUL': 227, 'ISO3': 'ZAF', 'ISO2': 'ZA'},
                                'South Georgia and the South Sandwich Islands': {'GAUL': 228, 'ISO3': 'SGS',
                                                                                 'ISO2': 'GS'},
                                'South Sudan': {'GAUL': None, 'ISO3': 'SSD', 'ISO2': 'SS'},
                                'Spain': {'GAUL': 229, 'ISO3': 'ESP', 'ISO2': 'ES'},
                                'Sri Lanka': {'GAUL': 231, 'ISO3': 'LKA', 'ISO2': 'LK'},
                                'Sudan': {'GAUL': 40764, 'ISO3': 'SDN', 'ISO2': 'SD'},
                                'Suriname': {'GAUL': 233, 'ISO3': 'SUR', 'ISO2': 'SR'},
                                'Svalbard and Jan Mayen Islands': {'GAUL': 234, 'ISO3': 'SJM', 'ISO2': 'SJ'},
                                'Swaziland': {'GAUL': 235, 'ISO3': 'SWZ', 'ISO2': 'SZ'},
                                'Sweden': {'GAUL': 236, 'ISO3': 'SWE', 'ISO2': 'SE'},
                                'Switzerland': {'GAUL': 237, 'ISO3': 'CHE', 'ISO2': 'CH'},
                                'Syrian Arab Republic': {'GAUL': 238, 'ISO3': 'SYR', 'ISO2': 'SY'},
                                'Tajikistan': {'GAUL': 239, 'ISO3': 'TJK', 'ISO2': 'TJ'},
                                'Thailand': {'GAUL': 240, 'ISO3': 'THA', 'ISO2': 'TH'},
                                'The former Yugoslav Republic of Macedonia': {'GAUL': 241, 'ISO3': 'MKD', 'ISO2': 'MK'},
                                'Timor-Leste': {'GAUL': 242, 'ISO3': 'TLS', 'ISO2': 'TL'},
                                'Togo': {'GAUL': 243, 'ISO3': 'TGO', 'ISO2': 'TG'},
                                'Tokelau': {'GAUL': 244, 'ISO3': 'TKL', 'ISO2': 'TK'},
                                'Tonga': {'GAUL': 245, 'ISO3': 'TON', 'ISO2': 'TO'},
                                'Trinidad and Tobago': {'GAUL': 246, 'ISO3': 'TTO', 'ISO2': 'TT'},
                                'Tunisia': {'GAUL': 248, 'ISO3': 'TUN', 'ISO2': 'TN'},
                                'Turkey': {'GAUL': 249, 'ISO3': 'TUR', 'ISO2': 'TR'},
                                'Turkmenistan': {'GAUL': 250, 'ISO3': 'TKM', 'ISO2': 'TM'},
                                'Turks and Caicos islands': {'GAUL': 251, 'ISO3': 'TCA', 'ISO2': 'TC'},
                                'Tuvalu': {'GAUL': 252, 'ISO3': 'TUV', 'ISO2': 'TV'},
                                'U.K. of Great Britain and Northern Ireland': {'GAUL': 256, 'ISO3': 'GBR',
                                                                               'ISO2': 'GB'},
                                'Uganda': {'GAUL': 253, 'ISO3': 'UGA', 'ISO2': 'UG'},
                                'Ukraine': {'GAUL': 254, 'ISO3': 'UKR', 'ISO2': 'UA'},
                                'United Arab Emirates': {'GAUL': 255, 'ISO3': 'ARE', 'ISO2': 'AE'},
                                'United Republic of Tanzania': {'GAUL': 257, 'ISO3': 'TZA', 'ISO2': 'TZ'},
                                'United States Virgin Islands': {'GAUL': 258, 'ISO3': 'VIR', 'ISO2': 'VI'},
                                'United States of America': {'GAUL': 259, 'ISO3': 'USA', 'ISO2': 'US'},
                                'Uruguay': {'GAUL': 260, 'ISO3': 'URY', 'ISO2': 'UY'},
                                'Uzbekistan': {'GAUL': 261, 'ISO3': 'UZB', 'ISO2': 'UZ'},
                                'Vanuatu': {'GAUL': 262, 'ISO3': 'VUT', 'ISO2': 'VU'},
                                'Venezuela': {'GAUL': 263, 'ISO3': 'VEN', 'ISO2': 'VE'},
                                'Viet Nam': {'GAUL': 264, 'ISO3': 'VNM', 'ISO2': 'VN'},
                                'Wallis and Futuna': {'GAUL': 266, 'ISO3': 'WLF', 'ISO2': 'WF'},
                                'Western Sahara': {'GAUL': 268, 'ISO3': 'ESH', 'ISO2': 'EH'},
                                'Yemen': {'GAUL': 269, 'ISO3': 'YEM', 'ISO2': 'YE'},
                                'Zambia': {'GAUL': 270, 'ISO3': 'ZMB', 'ISO2': 'ZM'},
                                'Zimbabwe': {'GAUL': 271, 'ISO3': 'ZWE', 'ISO2': 'ZW'}}


    def create_dropdown(self, dropdown_options, description, default_value):
        """
        Create a dropdown widget with the given options, description, and default value.

        :param dropdown_options: a list of options for the dropdown
        :type dropdown_options: list
        :param description: the description text for the dropdown
        :type description: str
        :param default_value: the default value for the dropdown
        :type default_value: any
        :return: the created dropdown widget
        :rtype: widgets.Dropdown
        """
        dropdown = widgets.Dropdown(
            options=dropdown_options,
            value=default_value,  # the default value
            description=description,
            disabled=False,
        )

        dropdown.observe(self.on_dropdown_change, names='value')
        return dropdown

    def create_widgets(self):
        self.boundary_type = widgets.ToggleButtons(
            options=['Predefined Boundaries', 'User Defined', 'User Uploaded Data', 'Parameter File'],
            disabled=False,
            value='Predefined Boundaries',
            tooltips=['Predefined Boundaries (such as watersheds or administrative boundaries)',
                      'User Defined (draw a polygon on the map)',
                      'User Uploaded Data (upload a shapefile, kml, or kmz)',
                      'Parameter file generated during a past run or setup.'],
        )

        self.dropdown = self.create_dropdown(boundary_dropdown, 'Select Boundary:', 'watersheds_4')
        # self.dropdown.layout.width = 'auto'

        self.dropdown_api = self.create_dropdown({'GloFas': 'glofas',
                                                  'Google Earth Engine': 'gee',
                                                  'MODIS NRT Flood Data': 'modis_nrt',
                                                  'WorldPop': 'worldpop',
                                                  'Global Flood Database': 'global_flood_database'},
                                                 'Select API:',
                                                 'glofas')
        # self.dropdown_api.layout.width = 'auto'

        self.add_to_map_check = widgets.Checkbox(value=True, description='Add Downloaded Image to Map')
        self.btn = widgets.Button(description='Process')
        self.btn.layout.width = '100%'
        self.btn.style.button_color = '#c8102e'
        self.btn.style.text_color = 'white'

        self.instruction_text = widgets.Text(value='Draw one or more polygons on the map', disabled=True)
        self.instruction_text.style.text_color = '#c8102e'
        self.upload_widget = widgets.FileUpload(accept='.geojson', multiple=False)
        self.upload_widget.layout.width = '100%'
        self.upload_widget.style.button_color = '#c8102e'
        self.upload_widget.style.text_color = 'white'

        self.no_data_helper_checklist = widgets.Checkbox(value=True, description='No-Data Helper Function',
                                                         tooltip="Due to GloFas API framework, some versions and/or "
                                                                 "models aren't available for certain dates. If enabled,"
                                                                 "This will allow the program to automatically alter the version date and "
                                                                 "hydrological model to find a matching dataset.")

        self.boundary_stack = VBox([self.dropdown, self.instruction_text, self.upload_widget])

        self.api_choice_stack = VBox([])

        self.end_of_vbox_items = VBox([self.add_to_map_check, self.no_data_helper_checklist])

        self.predefined_upload_widget = widgets.FileUpload(
            accept='.json',
            multiple=False  # True to accept multiple files upload else False
        )

        self.predefined_upload_widget.layout.display = 'none'
        self.predefined_upload_widget.layout.width = '100%'
        self.predefined_upload_widget.style.button_color = '#c8102e'
        self.predefined_upload_widget.style.text_color = 'white'

        self.glofas_stack = VBox([])

        max_width_value = '600px'

        self.out = Output(layout=Layout(max_height='10vh', overflow_y='scroll'))

        self.inner_widget_container = VBox(
            [self.boundary_type, self.boundary_stack, self.dropdown_api, self.api_choice_stack,
             self.predefined_upload_widget, self.btn, self.out],
            layout=Layout(width='100%', max_width=max_width_value)  # Set the width to '100%' and max_width to '50%'
        )

        # self.widget_container = VBox(
        #     [self.inner_widget_container],
        #     layout=Layout(justify_content='center', width='100%', max_height='40vh', overflow_y='scroll')  # Set the width of the outer container to '100%'
        # )

        for widget in [self.dropdown, self.dropdown_api, self.btn, self.out]:
            widget.layout.width = '100%'

        self.userlayers = {}


        self.create_sub_folder = widgets.Checkbox(
            value=True,
            description='Create Subfolder',
            disabled=False,
            indent=False
        )

        self.clip_to_geometry = widgets.Checkbox(
            value=True,
            description='Clip Image to Geometry Bounds',
            disabled=False,
            indent=False
        )

        self.keep_individual_tiles = widgets.Checkbox(
            value=False,
            description='Keep Individual Tiles',
            disabled=False,
            indent=False
        )

        self.add_image_to_map = widgets.Checkbox(
            value=True,
            description='Add Image to Map',
            disabled=False,
            indent=False
        )

        self.filechooser = fc.FileChooser(os.getcwd(), show_only_dirs=True)

    def setup_event_listeners(self):
        """
        Set up event listeners for the given parameters.

        :return: None
        """
        self.boundary_type.observe(self.on_boundary_type_change, names='value')
        self.dropdown.observe(self.on_dropdown_change, names='value')
        self.dropdown_api.observe(self.on_api_change, names='value')
        self.btn.on_click(self.on_button_click)
        self.upload_widget.observe(self.on_file_upload, names='value')

    def initialize_ui_state(self):
        """
        Initializes the UI state by setting initial values and visibility for various elements.

        :return: None
        """
        self.on_dropdown_change({'new': self.dropdown.value})
        self.on_api_change({'new': self.dropdown_api.value})
        self.on_boundary_type_change({'new': self.boundary_type.value})
        self.on_file_upload({'new': self.upload_widget.value})

        # Set initial visibility for instruction text and upload widget
        self.instruction_text.layout.display = 'none'

        self.upload_widget.layout.display = 'none'

        self.on_api_change({'new': self.dropdown_api.value})

        # Add the main widget container to the display
        self.add_widget(self.inner_widget_container,
                        layout=Layout(justify_content='center', max_height='40vh', overflow='auto'))

    def create_dropdown(self, dropdown_options, description, default_value):
        """
        Create a dropdown widget with the given options, description, and default value.

        :param dropdown_options: a list of options for the dropdown
        :type dropdown_options: list
        :param description: the description text for the dropdown
        :type description: str
        :param default_value: the default value for the dropdown
        :type default_value: any
        :return: the created dropdown widget
        :rtype: widgets.Dropdown
        """
        dropdown = widgets.Dropdown(
            options=dropdown_options,
            value=default_value,  # the default value
            description=description,
            disabled=False,
        )

        dropdown.observe(self.on_dropdown_change, names='value')
        return dropdown

    # def update_gee_date_selection_box(self, change):

    def toggle_minimize(self, b):
        """
        Toggles the visibility of the main content and changes the button text between 'Minimize' and 'Maximize'.

        :param b: A boolean value indicating whether to minimize or maximize the content.
        :type b: bool
        :return: None
        """
        # This function is called when the minimize button is clicked.
        if self.main_content.layout.display == 'none':
            # If the content is hidden, show it and change button text to 'Minimize'
            self.main_content.layout.display = 'block'
            self.minimize_button.description = 'Minimize'
        else:
            # If the content is shown, hide it and change button text to 'Maximize'
            self.main_content.layout.display = 'none'
            self.minimize_button.description = 'Maximize'

    def geometry_to_geodataframe(self):
        """
        Converts the geometry dictionary to a GeoDataFrame.

        :return: A GeoDataFrame containing the converted geometry.
        """
        # Convert the geometry dictionary to a shape
        geometry_shape = shape(self.geometry)

        # Create a GeoDataFrame from the shape
        return gpd.GeoDataFrame([{'geometry': geometry_shape}], crs='EPSG:4326')

    def inspect_grib_file(self, file_path):
        """
        Inspects a GRIB file at the given file path and prints information about each message in the file.

        :param file_path: The path to the GRIB file.
        :return: None
        """
        try:
            # Open the GRIB file
            grib_file = pygrib.open(file_path)

            # Count the number of messages
            num_messages = grib_file.messages

            for i in range(1, num_messages + 1):
                # Read each message
                message = grib_file.message(i)

                try:
                    # Attempt to read the data array
                    data = message.values
                except Exception as e:
                    # Handle cases where data can't be read
                    print(f"  - An error occurred when reading data: {e}")

                print("")

        except Exception as e:
            print(f"An overall error occurred: {e}")

    # Replace 'your_grib_file.grib' with the path to your actual GRIB file

    def calculate_bounds(self, geojson_content):
        """
        Calculate the bounds of a given GeoJSON content.

        :param geojson_content: The GeoJSON content to calculate the bounds from.
        :return: A list of two lists representing the minimum and maximum latitude and longitude coordinates respectively.
        """
        # Initialize min and max coordinates
        min_lat, min_lon, max_lat, max_lon = 90, 180, -90, -180

        # Function to update the bounds based on a coordinate pair
        def update_bounds(lat, lon):
            nonlocal min_lat, min_lon, max_lat, max_lon
            if lat < min_lat: min_lat = lat
            if lon < min_lon: min_lon = lon
            if lat > max_lat: max_lat = lat
            if lon > max_lon: max_lon = lon

        # Iterate through the coordinates and update the bounds
        for feature in geojson_content['features']:
            coords = feature['geometry']['coordinates']
            geom_type = feature['geometry']['type']

            # Update bounds based on the geometry type
            if geom_type == 'Point':
                update_bounds(*coords)
            elif geom_type in ['LineString', 'MultiPoint']:
                for coord in coords:
                    update_bounds(*coord)
            elif geom_type in ['Polygon', 'MultiLineString']:
                for part in coords:
                    for coord in part:
                        update_bounds(*coord)
            elif geom_type == 'MultiPolygon':
                for polygon in coords:
                    for part in polygon:
                        for coord in part:
                            update_bounds(*coord)

        return [[min_lat, min_lon], [max_lat, max_lon]]

    def on_file_upload(self, change):
        """
        Method to process uploaded files and create a GeoJSON layer.

        :param change: A dictionary containing the uploaded file info.
        :return: None
        """
        uploaded_files = change['new']  # Get the list of uploaded file info

        try:
            # Process each uploaded file
            for file_info in uploaded_files:
                filename = file_info['name']

                # This is the file content as a memoryview object
                content = file_info['content']

                # Convert the memoryview object to bytes then decode to string
                content_str = bytes(content).decode("utf-8")

                # Load the string as GeoJSON
                geojson_content = geojson.loads(content_str)

                # Create a GeoJSON layer

                style = {
                    "color": "black",  # Line color
                    "fillColor": "black",  # Fill color
                    "weight": 1,  # Border width
                    "fillOpacity": 0.5  # Fill opacity
                }

                geojson_layer = GeoJSON(data=geojson_content, style=style)

                # Add the GeoJSON to the map
                try:
                    self.add_layer(geojson_layer,
                                   name='User Uploaded Data',
                                   vis_params={'color': 'black'})
                    # bounds = self.calculate_bounds(geojson_content)
                    # self.fit_bounds(bounds)
                    self.userlayers['User Uploaded Data'] = geojson_layer
                except Exception as e:
                    with self.out:
                        self.out.clear_output()
                        print(f"Error adding layer: {e}")

        except Exception as e:
            with self.out:
                self.out.clear_output()
                print(f"Error processing files: {e}")

    def convert_to_cog(self, input_path, output_path):
        """
        Convert a GeoTIFF to a COG (Cloud-Optimized GeoTIFF) using gdal_translate.

        :param input_path: Full path to the input GeoTIFF file.
        :type input_path: str
        :param output_path: Full path to the output COG file.
        :type output_path: str
        :return: None
        """
        # Convert a GeoTIFF to a COG using gdal_translate
        cmd = [
            'gdal_translate',
            '-of', 'COG',
            '-co', 'COMPRESS=DEFLATE',
            '-ot', 'Float64',  # Adjust the compression as needed
            input_path,
            output_path
        ]
        subprocess.run(cmd, check=True)

    def convert_grib_to_geotiff(self, grib_path, geotiff_path):
        """
        Converts a GRIB file to a standard GeoTIFF using gdal_translate.

        :param grib_path: The path to the input GRIB file.
        :param geotiff_path: The path to save the output GeoTIFF file.
        :return: None

        This method uses the `gdal_translate` command to convert the input GRIB file to a GeoTIFF file. The output GeoTIFF file will be saved at the specified `geotiff_path` location.

        **Note:** The `gdal_translate` command is executed using the `subprocess.run()` method with the `check=True` parameter to ensure the conversion process completes without any errors.

        Example usage:

        ```python
        # Instantiate the object
        converter = Converter()

        # Convert a GRIB file to GeoTIFF
        converter.convert_grib_to_geotiff('/path/to/input.grib', '/path/to/output.tif')
        ```
        """
        # Convert a GRIB file to a standard GeoTIFF using gdal_translate
        cmd = [
            'gdal_translate',
            '-of', 'GTiff',
            '-ot', 'Float64',
            grib_path,
            geotiff_path
        ]
        subprocess.run(cmd, check=True)

    def get_edge_values(self, raster_array, transform, shape, geometry):
        """
        Get the edge values of a raster within a specified geometry.

        :param raster_array: The array representing the raster.
        :param transform: The affine transformation matrix to transform coordinates from pixel space to world space.
        :param shape: The shape of the output raster array.
        :param geometry: The geometry within which to find the edge values.
        :return: An array containing the unique edge values found within the specified geometry.

        """
        # Create a mask for the geometry
        mask = geometry_mask([geometry], transform=transform, invert=True, out_shape=shape)

        # Find the edge values of the raster
        edge_values = np.unique(raster_array[mask])
        return edge_values

    def get_nodata_value(self, src):
        """
        Method: get_nodata_value

        This method is used to retrieve the no-data value from a given data source.

        :param src: The data source from which to retrieve the no-data value.
        :return: The no-data value of the source, if available. Otherwise, it infers the no-data value from data statistics or common conventions.

        """
        # Try to get no-data value from source metadata
        if src.nodata is not None:
            return src.nodata

        # If no-data value isn't set, infer it from data statistics or common conventions
        data_sample = src.read(1, masked=True)  # Read first band as a sample
        common_nodata_values = [-9999, -999, 0]  # Add common no-data values for your data

        for nodata_candidate in common_nodata_values:
            if np.isclose(data_sample, nodata_candidate).mean() > 0.5:  # More than 50% matches
                return nodata_candidate

        return -9999  # or 0, or whatever makes sense for your data

    def create_mask(self, out_image, nodata_value):
        """
        Method to create a mask based on a given output image and no-data value.

        :param out_image: The output image to create the mask from.
        :param nodata_value: The no-data value used to determine the mask.
        :return: The mask created based on the output image and no-data value.

        """
        if nodata_value is None:
            # If no no-data value is known, you might need a custom strategy
            # Perhaps infer the no-data value based on data distribution
            nodata_value = self.get_nodata_value(out_image)  # This would be a custom function you'd need to implement

        if isinstance(nodata_value, float):
            # Use a tolerance for floating-point comparisons
            tolerance = 1e-6  # Adjust based on your data's precision
            return np.isclose(out_image, nodata_value, atol=tolerance)
        else:
            # Direct comparison for integer types
            return out_image == nodata_value

    def clip_raster(self, file_path, geometry):
        """
        :param file_path: The file path of the raster file (GRIB or TIFF) to be clipped.
        :param geometry: The geometry to clip the raster file.
        :return: The file path of the clipped TIFF file.
        """

        # Check file format and inspect if it's a GRIB file

        if file_path.endswith('.grib'):
            self.inspect_grib_file(file_path)

        # Convert Earth Engine geometry to shapely geometry
        geometry = self.ee_geometry_to_shapely(geometry)

        # Convert to MultiPolygon if needed
        if isinstance(geometry, dict):
            try:
                geometry = shape(geometry['geometries'][1])
            except KeyError:
                geometry = shape(geometry)
        if not isinstance(geometry, MultiPolygon):
            geometry = MultiPolygon([geometry])

        # Create a GeoDataFrame
        gdf = gpd.GeoDataFrame([{'geometry': geometry}], crs="EPSG:4326")

        # Open the raster file with rasterio
        with rasterio.open(file_path) as src:

            # Reproject the geometry to match the raster's CRS
            gdf = gdf.to_crs(src.crs)

            # Read the raster data
            raster_data = src.read(1)

            # Determine the nodata value based on the data type
            if raster_data.dtype == 'uint8':
                nodata_value = 255
            else:
                nodata_value = -9999

            # Create the mask
            mask = geometry_mask(gdf.geometry, transform=src.transform, invert=True,
                                 out_shape=(src.height, src.width))

            # Apply the mask - set nodata values
            raster_data[~mask] = nodata_value

            # Define output path
            output_path = file_path.rsplit('.', 1)[0] + '_clipped.tif'

            # Write the masked data to a new raster file
            with rasterio.open(
                output_path,
                'w',
                driver='GTiff',
                height=src.height,
                width=src.width,
                count=1,
                dtype=raster_data.dtype,
                crs=src.crs,
                transform=src.transform,
                nodata=nodata_value
            ) as dst:
                dst.write(raster_data, 1)

        return output_path

    def on_dropdown_change(self, change):
        """
        :param change: A dictionary containing information about the dropdown change event.
        :return: None

        This method is called when the value of a dropdown menu is changed. It takes in the `change` parameter, which is a dictionary that contains information about the change event.

        The method first extracts the new value from the `change` dictionary.

        It then proceeds to remove any existing layers by iterating over the `added_layers` dictionary and removing each layer from the `layers` list. It also resets the `added_layers` dictionary
        *.

        Next, it splits the new value into two parts using the underscore (_) as the delimiter.

        If the first part of the new value is 'admin', it adds the states layer based on the second part of the new value. It creates a feature collection based on the specified GAUL dataset
        * and level, and then creates an EE tile layer using the feature collection. The layer variable is updated with the new feature collection, and the column variable is set to the corresponding
        * administrative name column. The new layer is added to the map using the `add_layer` method, and the layer is also stored in the `added_layers` dictionary.

        If the first part of the new value is 'watersheds', it adds the HydroSHEDS layer based on the second part of the new value. It creates a feature collection based on the specified Hydro
        *SHEDS dataset, and then creates an EE tile layer using the feature collection. The layer variable is updated with the new feature collection, and the column variable is set to the Hydro
        *SHEDS ID column. The new layer is added to the map using the `add_layer` method, and the layer is also stored in the `added_layers` dictionary.
        """
        new_value = change['new']

        # Remove any existing layers
        for name, layer in self.added_layers.items():
            if layer in self.layers:
                self.remove_layer(layer)
        self.added_layers = {}

        new_value = new_value.split('_')

        # Add the appropriate layer based on the selection
        if new_value[0] == 'admin':
            # Add the states layer for 'admin_0'.
            states = ee.FeatureCollection(f"FAO/GAUL_SIMPLIFIED_500m/2015/level{new_value[1]}")
            states_layer = geemap.ee_tile_layer(states, {}, 'US States')
            self.layer = states
            self.column = f'ADM{new_value[1]}_NAME'
            self.add_layer(states_layer)
            self.added_layers[f'admin_{1}'] = states_layer
        elif new_value[0] == 'watersheds':
            hydrosheds = ee.FeatureCollection(f"WWF/HydroSHEDS/v1/Basins/hybas_{new_value[1]}")
            # Add the HydroSHEDS layer for 'watersheds_4'.
            hydrosheds_layer = geemap.ee_tile_layer(hydrosheds, {}, 'HydroSHEDS Basins')
            self.layer = hydrosheds
            self.column = 'HYBAS_ID'
            self.add_layer(hydrosheds_layer)
            self.added_layers[f'watersheds_{new_value[1]}'] = hydrosheds_layer

    def on_api_change(self, change):
        """
        :param change: dictionary containing the change information
            - 'new': the new value of the change
        :return: None

        This method is called when there is a change in the API selection. The `change` parameter is a dictionary that contains information about the change. The 'new' key in the dictionary
        * represents the new value of the change.

        Depending on the new value of the change, this method performs different actions. If the new value is 'glofas', it creates a dropdown menu for GloFas products and sets up the necessary
        * event listener. It then updates the API choice stack to display the GloFas options.

        If the new value is 'gee', it creates widgets for Google Earth Engine (GEE) options. It then updates the API choice stack to display the GEE options.

        If the new value is neither 'glofas' nor 'gee', no action is taken.

        Note that the commented code in the method is not executed.

        Examples:
            # Example usage
            change = {'new': 'glofas'}
            on_api_change(self, change)
        """
        new_value = change['new']

        # Remove any existing layers
        # for name, layer in self.added_layers.items():
        #     if layer in self.layers:
        #         self.remove_layer(layer)
        # self.added_layers = {}

        # Add the appropriate layer based on the selection
        if new_value == 'glofas':
            self.glofas_options = self.create_glofas_dropdown([x for x in self.glofas_dict['products'].keys()],
                                                              description='Select GloFas Product:',
                                                              default_value='cems-glofas-forecast')
            self.glofas_options.layout.width = 'auto'
            self.glofas_options.observe(self.on_glofas_option_change, names='value')
            self.on_glofas_option_change({'new': self.glofas_options.value})
            self.api_choice_stack.children = [self.glofas_options, self.glofas_stack]
            if self.boundary_type.value == 'Predefined Boundaries':
                self.update_boundary_options('Predefined Boundaries')

        elif new_value == 'gee':
            self.gee_options = self.create_widgets_gee()
            # self.gee_options.layout.width = 'auto'
            self.api_choice_stack.children = tuple(self.gee_options)
            if self.boundary_type.value == 'Predefined Boundaries':
                self.update_boundary_options('Predefined Boundaries')
        elif new_value == 'modis_nrt':
            self.modis_nrt_options = self.create_widgets_for_modis_nrt()
            self.api_choice_stack.children = tuple(self.modis_nrt_options)
            if self.boundary_type.value == 'Predefined Boundaries':
                self.update_boundary_options('Predefined Boundaries')

        elif new_value == 'worldpop':
            self.worldpop_options = self.create_widgets_for_worldpop()
            self.api_choice_stack.children = tuple(self.worldpop_options)
            if self.boundary_type.value == 'Predefined Boundaries':
                self.update_boundary_options('Predefined Boundaries')
        elif new_value == 'global_flood_database':
            self.global_flood_db_options = self.create_widgets_for_global_flood_db()
            self.api_choice_stack.children = tuple(self.global_flood_db_options)
            if self.boundary_type.value == 'Predefined Boundaries':
                self.update_boundary_options('Predefined Boundaries')
        else:
            pass

    def on_boundary_type_change(self, change):
        """
        :param change: A dictionary representing the change that occurred in the boundary type. The dictionary should have a key 'new' which points to the new boundary value.
        :return: None

        This method updates the boundary options based on the new boundary value provided in the change dictionary. The updated options are passed to the method 'update_boundary_options'.
        """
        boundary_value = change['new']
        self.update_boundary_options(boundary_value)

    def update_boundary_options(self, boundary_value):
        """
        Method Name: update_boundary_options

        Description: This method updates the boundary options based on the selected boundary value.

        Parameters:
        - boundary_value (str): The selected boundary value.

        Returns:
        None

        """
        # Define how the boundary type affects the boundary dropdown options
        if boundary_value == 'Predefined Boundaries':
            self.on_dropdown_change({'new': self.dropdown.value})
            # Predefined boundaries selected
            self.dropdown.layout.display = 'block'  # Show the dropdown
            self.instruction_text.layout.display = 'none'  # Hide the instruction text
            self.upload_widget.layout.display = 'none'  # Hide the upload widget
            self.predefined_upload_widget.layout.display = 'none'
            self.end_of_vbox_items.layout.display = 'block'
            self.boundary_stack.layout.display = 'block'
            self.dropdown_api.layout.display = 'block'
            self.api_choice_stack.layout.display = 'block'

        elif boundary_value in ['User Defined', 'User Uploaded Data']:
            # Either User defined or User uploaded data selected

            # Remove EE Leaflet Tile Layers with Google Earth Engine attribution
            for layer in self.layers:
                if hasattr(layer, 'attribution') and 'Google Earth Engine' in layer.attribution:
                    self.remove_layer(layer)

            if boundary_value == 'User Defined':
                # User defined selected
                self.dropdown.layout.display = 'none'  # Hide the dropdown
                self.instruction_text.layout.display = 'block'  # Show the instruction text
                self.upload_widget.layout.display = 'none'  # Hide the upload widget
                self.predefined_upload_widget.layout.display = 'none'
                self.end_of_vbox_items.layout.display = 'block'
                self.boundary_stack.layout.display = 'block'
                self.dropdown_api.layout.display = 'block'
                self.api_choice_stack.layout.display = 'block'

            elif boundary_value == 'User Uploaded Data':
                # User uploaded data selected
                self.dropdown.layout.display = 'none'  # Hide the dropdown
                self.instruction_text.layout.display = 'none'  # Hide the instruction text
                self.upload_widget.layout.display = 'block'  # Show the upload widget
                self.predefined_upload_widget.layout.display = 'none'
                self.end_of_vbox_items.layout.display = 'block'
                self.boundary_stack.layout.display = 'block'
                self.dropdown_api.layout.display = 'block'
                self.api_choice_stack.layout.display = 'block'

        elif boundary_value == 'Parameter File':
            self.predefined_upload_widget.layout.display = 'block'
            self.end_of_vbox_items.layout.display = 'none'
            self.boundary_stack.layout.display = 'none'
            self.dropdown_api.layout.display = 'none'
            self.api_choice_stack.layout.display = 'none'

        else:
            # Default case, hide everything
            self.dropdown.layout.display = 'none'
            self.instruction_text.layout.display = 'none'
            self.upload_widget.layout.display = 'none'


    def ensure_multipolygon(self, geometry):
        """
            Ensures that the given geometry is a MultiPolygon. If the geometry is a Polygon, it converts it into a MultiPolygon.

            :param geometry: The geometry object to ensure as a MultiPolygon.
            :return: The input geometry as a MultiPolygon or the original geometry if it is already a MultiPolygon.

            **Example Usage**

            .. code-block:: python

                geometry = ee.Geometry.Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
                ensure_multipolygon(geometry)

            **Example Output**

            .. code-block:: python

                <ee.Geometry.MultiPolygon object at 0x7f672fc35160>
        """
        if geometry.type().getInfo() == 'Polygon':
            return ee.Geometry.MultiPolygon([geometry.coordinates()])
        else:
            return geometry

    def ee_geometry_to_shapely(self, geometry):
        """
        Convert an Earth Engine Geometry, Feature, or GeoJSON to a Shapely Geometry object.

        :param geometry: An Earth Engine Geometry, Feature, or GeoJSON dictionary.
        :return: A Shapely Geometry object.

        """
        # Check if the geometry is an Earth Engine Geometry or Feature
        if isinstance(geometry, ee.Geometry) or isinstance(geometry, ee.Feature):
            # Convert Earth Engine object to GeoJSON
            geo_json = geometry.getInfo()
            if 'geometry' in geo_json:  # If it's a Feature, extract the geometry part
                geo_json = geo_json['geometry']
            # Convert GeoJSON to a Shapely Geometry
            return shape(geo_json)
        elif isinstance(geometry, dict):  # Directly convert from GeoJSON if it's a dictionary
            return shape(geometry)
        else:
            # If it's neither, assume it's already a Shapely Geometry or compatible
            return geometry

    def on_button_click(self, b):
        """
        Function to handle button click event.

        :param b: Button object representing the clicked button.
        :return: None
        """
        with self.out:
            self.out.clear_output()  # Clear the previous output
        self.draw_and_process()

        # Assuming `distinct_values` is available after drawing and processing

    def get_bounding_box(self, distinct_values=None, feature=None):
        """
        :param distinct_values: A list of distinct values used for filtering the layer data
        :param feature: An optional feature object used for defining a custom geometry
        :return: The bounding box of the selected data

        This method calculates the bounding box of the selected data based on the provided parameters. If distinct_values is specified, it filters the layer data based on the values in distinct
        *_values and returns the bounding box of the filtered data. If feature is specified, it converts the feature to a GeoDataFrame and returns the bounding box of the geometry. If neither
        * distinct_values nor feature is provided, it returns the bounding box of the dissolved geometry of the User Uploaded Data.

        Example usage:
        ----------------
        distinct_values = ['value1', 'value2']
        feature = ee.Feature()

        bounding_box = get_bounding_box(distinct_values, feature)
        print(bounding_box)
        """

        if distinct_values:
            if self.dropdown.value.split('_')[0] == 'admin':
                bounds = self.layer.filter(ee.Filter.inList(self.column, distinct_values)).geometry().bounds().getInfo()
                gdf = gpd.GeoDataFrame([{'geometry': shape(bounds)}], crs='EPSG:4326')
                return gdf.geometry.bounds
            elif self.dropdown.value.split('_')[0] == 'watersheds':
                bounds = self.layer.filter(
                    ee.Filter.inList(self.column, distinct_values)).geometry().bounds().getInfo()
                gdf = gpd.GeoDataFrame([{'geometry': shape(bounds)}], crs='EPSG:4326')
                return gdf.geometry.bounds
        if 'User Uploaded Data' in self.userlayers and self.boundary_type.value == 'User Uploaded Data':
            gdf = gpd.GeoDataFrame.from_features(self.userlayers['User Uploaded Data'].data)
            dissolved_gdf = gdf.dissolve()
            self.geometry = dissolved_gdf.geometry.iloc[0]
            return dissolved_gdf.geometry.bounds

        elif self.draw_layer and self.boundary_type.value == 'User Defined':
            if feature:
                if isinstance(feature, ee.Feature):
                    feature_info = feature.getInfo()  # This converts the GEE Feature to a Python dictionary
                    geometry = feature_info['geometry']
                gdf = gpd.GeoDataFrame([{'geometry': shape(geometry)}], crs='EPSG:4326')
                self.geometry = gdf.geometry.iloc[0]
                return gdf.geometry.bounds

    def draw_and_process(self):
        """
        Draw and process data based on the boundary type.

        :return: None
        """
        if self.boundary_type.value == 'Parameter File':
            self.handle_parameter_file()
        else:
            self.process_based_on_api_selection()

    def handle_parameter_file(self):
        """
        Handle parameter file logic.

        :return: None
        """
        # Handle parameter file logic here
        pass

    def download_feature_geometry(self, distinct_values):
        """
        Downloads the geometry for each distinct value from the specified feature layer and stores it in self.geometry.

        :param distinct_values: A list of distinct values for filtering the feature layer.
        :return: None
        """
        if not distinct_values:
            print("No distinct values provided.")
            return

        feature_type_prefix = self.dropdown.value.split('_')[0]

        if feature_type_prefix not in ['watersheds', 'admin']:
            print("Invalid feature type.")
            return

        all_geometries = []

        for value in distinct_values:
            feature = self.layer.filter(ee.Filter.eq(self.column, value)).first()
            if not feature:
                print("No feature found for value:", value)
                continue

            geometry = feature.geometry()
            if not geometry:
                print("No geometry for value:", value)
                continue

            geometry_type = geometry.type().getInfo()

            if geometry_type == 'Polygon':
                all_geometries.append(geometry.coordinates().getInfo())
            elif geometry_type == 'MultiPolygon':
                for poly in geometry.coordinates().getInfo():
                    all_geometries.append(poly)
            elif geometry_type == 'GeometryCollection':
                self.process_geometry_collection(geometry, all_geometries)

        if all_geometries:
            try:
                dissolved_geometry = ee.Geometry.MultiPolygon(all_geometries).dissolve()
                feature = ee.Feature(dissolved_geometry)
            except ee.EEException as e:
                print("Error creating dissolved geometry:", e)
        else:
            print("No valid geometries to dissolve.")

        if feature and self.dropdown_api.value in ['glofas', 'modis_nrt']:
            self.geometry = feature.geometry().getInfo()
            with open('geometry.geojson', "w") as file:
                json.dump(self.geometry, file)
            return self.geometry
        else:
            self.geometry = feature.geometry()
            return self.geometry

    def process_geometry_collection(self, geometry_collection, all_geometries):
        """
        Processes a geometry collection and appends the coordinates of polygons and multipolygons to a list.

        :param geometry_collection: A geometry collection object.
        :param all_geometries: A list to store the coordinates of polygons and multipolygons.
        :return: None
        """
        geometries = geometry_collection.geometries().getInfo()
        for geom in geometries:
            geom_type = geom['type']
            if geom_type == 'Polygon':
                all_geometries.append(geom['coordinates'])
            elif geom_type == 'MultiPolygon':
                for poly in geom['coordinates']:
                    all_geometries.append(poly)

    def process_drawn_features(self, drawn_features):
        """
        Process the drawn features.

        :param drawn_features: A list of drawn features.
        :type drawn_features: list[ee.Feature or ee.Geometry]
        :return: A list of distinct values from the filtered layer.
        :rtype: list
        """
        all_distinct_values = []
        for feature in drawn_features:

            if isinstance(feature, ee.Feature) or isinstance(feature, ee.Geometry):
                drawn_geom = feature.geometry()
                bounding = drawn_geom.bounds()
                filtered_layer = self.layer.filterBounds(bounding)
                distinct_values = filtered_layer.aggregate_array(self.column).distinct().getInfo()
                all_distinct_values.extend(distinct_values)
        return list(set(all_distinct_values))

    def determine_geometries_to_process(self, override_boundary_type=None):
        """
        Determine the geometries to process based on the boundary type and user inputs.

        :return: A list of tuples representing the geometries to process. Each tuple contains a feature and distinct values.
        """
        with self.out:
            geometries = []
            if override_boundary_type:
                boundary_type = override_boundary_type
            else:
                boundary_type = self.boundary_type.value
            if boundary_type in ['Predefined Boundaries', 'User Defined']:
                for feature in self.draw_features:
                    if boundary_type == 'Predefined Boundaries':
                        distinct_values = self.process_drawn_features([feature])
                        feature = self.download_feature_geometry(distinct_values)
                    else:  # User Defined
                        distinct_values = None
                        # Assuming feature is the geometry itself in this case
                    geometries.append((feature, distinct_values))
            elif boundary_type == 'User Uploaded Data' and 'User Uploaded Data' in self.userlayers:
                feature = self.userlayers['User Uploaded Data'].data
                geometries.append((feature, None))
            return geometries

    def ee_ensure_geometry(self, geometry):
        """
        Ensures that the input geometry is a valid Earth Engine Geometry or Feature.

        :param geometry: The input geometry to be validated.
        :type geometry: ee.Geometry or ee.Feature
        :return: The valid Earth Engine Geometry.
        :rtype: ee.Geometry
        :raises ValueError: If the input geometry is neither an ee.Geometry nor an ee.Feature.
        """
        if isinstance(geometry, ee.Feature):
            geometry = geometry.geometry()
            return geometry
        elif isinstance(geometry, ee.Geometry):
            return geometry
        else:
            raise ValueError("Invalid geometry type. Must be an Earth Engine Geometry or Feature.")

    def convert_geojson_to_ee(self, geojson_obj):
        """
        Converts a GeoJSON object to Earth Engine feature or geometry.

        :param geojson_obj: A GeoJSON object.
        :return: A converted Earth Engine feature or geometry.

        Raises:
            ValueError: If the GeoJSON type is unsupported.

        Example usage:
            geojson = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [0, 0]
                }
            }
            ee_object = convert_geojson_to_ee(geojson)
        """
        if geojson_obj['type'] == 'FeatureCollection':
            return ee.FeatureCollection(geojson_obj['features'])
        elif geojson_obj['type'] == 'Feature':
            geometry = geojson_obj['geometry']
            return ee.Feature(geometry)
        elif geojson_obj['type'] in ['Polygon', 'MultiPolygon', 'Point', 'LineString', 'MultiPoint', 'MultiLineString']:
            return ee.Geometry(geojson_obj)
        else:
            raise ValueError("Unsupported GeoJSON type")

    def process_based_on_api_selection(self):
        """
        Process based on the selected API.

        :return: None
        """
        with self.out:
            geometries = self.determine_geometries_to_process()
            for index, (geometry, distinct_values) in enumerate(geometries):
                if self.dropdown_api.value == 'glofas':
                    self.process_glofas_api(geometry, distinct_values, index)
                elif self.dropdown_api.value == 'gee':
                    self.process_gee_api(geometry, distinct_values, index)
                elif self.dropdown_api.value == 'modis_nrt':
                    self.process_modis_nrt_api(geometry, distinct_values, index)
                elif self.dropdown_api.value == 'worldpop':
                    self.process_worldpop_api(geometry, distinct_values, index)
                else:
                    print('No valid API selected!')

    def process_and_clip_raster(self, file_path, geometry, params=None):
        """
        Process and clip a raster file.

        :param file_path: The file path of the raster file to be processed and clipped.
        :return: None
        """
        min_val, max_val, no_data_val = self.get_raster_min_max(file_path)
        if min_val == -9999:
            min_val = 0

        vis_params = {
            'min': min_val,
            'max': max_val,
            'palette': 'viridis',
            'nodata': no_data_val
        }
        if params['clip_to_geometry']:
            raster_path = self.clip_raster(file_path, geometry)
        else:
            raster_path = file_path
        if params['add_to_map']:
            self.add_clipped_raster_to_map(raster_path, vis_params=vis_params)

    def add_clipped_raster_to_map(self, raster_path, vis_params=None):
        """
        Adds a clipped raster to the map.

        :param raster_path: A string specifying the path to the raster file.
        :param vis_params: Optional dictionary specifying the visualization parameters for the raster. Default is an empty dictionary.
        :return: None

        Example usage:

            add_clipped_raster_to_map('/path/to/raster.tif', vis_params={'min': 0, 'max': 255})

        This method creates a `localtileserver.TileClient` object using the given raster path. It then uses the `localtileserver.get_leaflet_tile_layer` method to obtain the Leaflet tile layer
        * for the raster, applying the visualization parameters if provided. The resulting tile layer is added to the map using the `add_layer` method. Finally, the map adjusts its bounds to
        * fit the bounds of the raster using the `fit_bounds` method.

        If a ValueError occurs during the process, it will be caught and printed as an error message. Any other exceptions will also be caught and printed.

        Note: This method assumes that the necessary dependencies (`localtileserver`) are installed and importable.
        """
        if vis_params is None:
            vis_params = {}
        try:
            client = localtileserver.TileClient(raster_path)
            tile_layer = localtileserver.get_leaflet_tile_layer(client, **vis_params)
            self.add_layer(tile_layer)
            self.fit_bounds(client.bounds)
        except ValueError as e:
            print(f"ValueError: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

    def get_raster_min_max(self, raster_path):
        """
        :param raster_path: The file path to the raster file.
        :return: A tuple containing the minimum and maximum values of the raster.
        """

        dataset = gdal.Open(raster_path)
        band = dataset.GetRasterBand(1)  # Assumes the raster has only one band
        min_val = band.GetMinimum()
        max_val = band.GetMaximum()
        nodata_val = band.GetNoDataValue()

        band_data = band.ReadAsArray()

        # Check if 9999 is in the data
        if 9999 in band_data:
            # Mask the data to ignore values of 9999 or higher
            masked_data = np.ma.masked_where(band_data >= 9999, band_data)

            # Find the maximum value in the masked data
            next_highest_val = masked_data.max()

            # Set max_val to the next highest value
            max_val = next_highest_val

        # If the minimum and maximum values are not natively provided by the raster band
        if min_val is None or max_val is None:
            min_val, max_val = band.ComputeRasterMinMax(True)

        dataset = None  # Close the dataset
        return min_val, max_val, nodata_val



##GLOFAS COMPONENTS##
JupyterAPI.create_widgets_for_glofas = create_widgets_for_glofas
JupyterAPI.create_glofas_dropdown = create_glofas_dropdown
JupyterAPI.on_glofas_option_change = on_glofas_option_change
JupyterAPI.on_single_or_date_range_change = on_single_or_date_range_change
JupyterAPI.update_glofas_container = update_glofas_container
JupyterAPI.get_glofas_parameters = get_glofas_parameters
JupyterAPI.download_glofas_data = download_glofas_data
JupyterAPI.process_glofas_api = process_glofas_api

##EARTH ENGINE COMPONENTS##
JupyterAPI.create_widgets_gee = create_widgets_gee
JupyterAPI.on_gee_search_button_clicked = on_gee_search_button_clicked
JupyterAPI.on_gee_layer_selected = on_gee_layer_selected
JupyterAPI.on_single_or_range_dates_change = on_single_or_range_dates_change
JupyterAPI.gather_gee_parameters = gather_gee_parameters
JupyterAPI.process_gee_api = process_gee_api

##MODIS FLOOD COMPONENTS##
JupyterAPI.create_widgets_for_modis_nrt = create_widgets_for_modis_nrt
JupyterAPI.on_single_or_date_range_change_modis_nrt = on_single_or_date_range_change_modis_nrt
JupyterAPI.get_modis_nrt_dates = get_modis_nrt_dates
JupyterAPI.gather_modis_nrt_parameters = gather_modis_nrt_parameters
JupyterAPI.process_modis_nrt_api = process_modis_nrt_api

##WORLDPOP COMPONENTS##
JupyterAPI.create_widgets_for_worldpop = create_widgets_for_worldpop
JupyterAPI.process_worldpop_api = process_worldpop_api
JupyterAPI.gather_worldpop_parameters = gather_worldpop_parameters
JupyterAPI.download_and_split = download_and_split
JupyterAPI.mosaic_images = mosaic_images

##GLOBAL FLOOD DATABASE COMPONENTS##
JupyterAPI.create_widgets_for_global_flood_db = create_widgets_for_global_flood_db
