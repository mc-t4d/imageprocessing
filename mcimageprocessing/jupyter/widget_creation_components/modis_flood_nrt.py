import os
import re

import requests
from bs4 import BeautifulSoup
from osgeo import gdal

from mcimageprocessing.jupyter.widget_creation_components.gee import *
from mcimageprocessing.programmatic.APIs.ModisNRT import ModisNRT

modis_api = ModisNRT()

def on_single_or_date_range_change_modis_nrt(self, change):
    """
    Handles the change event when the option for single date or date range is changed.

    :param change: A dictionary containing information about the change event.
    :param glofas_option: The selected Glofas option.
    :return: None

    """

    single_or_date_range_value = change['new']

    if single_or_date_range_value == 'Single Date':
        # Create the DatePicker widget with constraints
        self.date_picker_modis_nrt = widgets.Dropdown(
            options=[(f"{x.year}-{x.month}-{x.day}", x) for x in self.modis_nrt_available_dates],
            description='Select Date:',
            disabled=False,
        )
        self.modis_nrt_date_vbox.children = [self.date_picker_modis_nrt]

    elif single_or_date_range_value == 'Date Range':
        # Create the DatePicker widgets with constraints
        self.date_picker_modis_nrt = HBox([
            DatePicker(
                description='Select Start Date:',
                disabled=False,
                value=min(self.modis_nrt_available_dates),  # Default value
                min=min(self.modis_nrt_available_dates),  # Minimum value
                max=max(self.modis_nrt_available_dates)  # Maximum value (assumes 31 days in max month)
            ),

            DatePicker(
                description='Select End Date:',
                disabled=False,
                value=max(self.modis_nrt_available_dates),  # Default value
                min=min(self.modis_nrt_available_dates),  # Minimum value
                max=max(self.modis_nrt_available_dates)  # Maximum value (assumes 31 days in max month)
            )])

        self.modis_nrt_date_vbox.children = [self.date_picker_modis_nrt]

    elif single_or_date_range_value == 'All Available Images':
        self.modis_nrt_date_vbox.children = []

    return single_or_date_range_value

def get_modis_nrt_dates(self):
    response = requests.get(
        'https://nrt3.modaps.eosdis.nasa.gov/api/v2/content/details/allData/61/MCDWD_L3_NRT?fields=all&formats=json')
    json_response = response.json()['content']
    years = [x['name'] for x in json_response if x['name'] != 'Recent']
    dates = []
    for year in years:
        date_response = requests.get(
            f'https://nrt3.modaps.eosdis.nasa.gov/api/v2/content/details/allData/61/MCDWD_L3_NRT/{year}?fields=all&formats=json')
        date_response_json = date_response.json()['content']
        for date in date_response_json:
            dates.append(self.convert_to_date(f'{year}{date["name"]}'))
    return dates

def create_widgets_for_modis_nrt(self):
    """
    Create widgets specific to GloFas Data Type 2

    :param glofas_option: The selected GloFas option
    :return: A list of widgets specific to the selected GloFas option
    """
    with self.out:
        self.modis_nrt_available_dates = modis_api.get_modis_nrt_dates()

        self.single_or_date_range_modis_nrt = widgets.ToggleButtons(
            options=['Single Date', 'Date Range', 'All Available Images'],
            disabled=False,
            value='Single Date',
            tooltips=['Single Date', 'Date Range', 'All Available Images'],
        )

        self.modis_nrt_band_selection = widgets.Dropdown(
            options=[x for x in modis_api.nrt_band_options.keys()],
            description='Band:',
            disabled=False,
            value='Flood 3-Day 250m Grid_Water_Composite',
            style={'description_width': 'initial'},
        )

        self.modis_nrt_date_vbox = VBox([])
        self.on_single_or_date_range_change_modis_nrt({'new': self.single_or_date_range_modis_nrt.value})

        self.single_or_date_range_modis_nrt.observe(
            lambda change: self.on_single_or_date_range_change_modis_nrt(change),
            names='value'
        )

        self.calculate_population = widgets.Checkbox(
            value=False,
            description='Calculate Population in Flood Area: ',
            disabled=False,
            indent=False
        )

        self.population_source = widgets.Dropdown(
            options=['WorldPop', 'GPWv4'],
            description='Population Source:',
            disabled=True,
            value='WorldPop',
            style={'description_width': 'initial'},
        )

        self.population_source_variable =  widgets.Dropdown(
            options=['Total Population', "Age-Sex Breakdown"],
            description='Population Variable:',
            disabled=True,
            value='Total Population',
            style={'description_width': 'initial'},
        )

        self.population_source_year = widgets.Dropdown(
            options=[x for x in range(2000, 2021)],
            description='Population Year:',
            disabled=True,
            value=2020,
            style={'description_width': 'initial'},
        )

        self.population_source_grid = widgets.Accordion([widgets.TwoByTwoLayout(
            top_left=self.calculate_population,
            top_right=self.population_source,
            bottom_left=self.population_source_variable,
            bottom_right=self.population_source_year
        )])

        self.population_source_grid.set_title(0, 'Population Options')

        self.end_of_vbox_items = widgets.Accordion([widgets.TwoByTwoLayout(
            top_left=self.create_sub_folder,
            top_right=self.clip_to_geometry,
            bottom_left=self.keep_individual_tiles,
            bottom_right=self.add_image_to_map
        )])

        self.end_of_vbox_items.set_title(0, 'Options')

        # Return a list of widgets
        return [self.modis_nrt_band_selection, self.single_or_date_range_modis_nrt, self.modis_nrt_date_vbox,
                self.filechooser, self.population_source_grid, self.end_of_vbox_items]

def process_modis_nrt_api(self, geometry, distinct_values, index):
    """
    :param geometry: The geometry of the area of interest.
    :param distinct_values: A boolean indicating whether distinct values should be used.
    :param index: The index for the MODIS NRT API.
    :return: None

    This method processes MODIS NRT API data for a given geometry, distinct values setting, and index. It first calculates the bounding box of the geometry using the provided distinct values
    *. It then gathers the required parameters for the MODIS NRT API. The parameters are printed to the console.

    If the 'create_sub_folder' parameter is True, a sub-folder is created with the current timestamp as the folder name. The 'folder_path' parameter is updated accordingly.

    Next, the method retrieves the MODIS tiles intersecting the bounding box. The tile numbers are printed to the console.

    The method then searches for matching files for each tile based on the provided year, day of year, and tile number. The URLs of the matching files are retrieved using requests and BeautifulSoup
    *.

    The method downloads the HDF files and saves them in the specified folder path. The paths to the downloaded HDF files are stored in the 'hdf_files_to_process' list.

    For each HDF file, the method opens it using GDAL and retrieves the subdatasets. It selects a subdataset and opens it. The subdataset is then converted to a GeoTIFF file. The paths to
    * the generated GeoTIFF files are stored in the 'tif_list' list.

    Upon completion of processing all HDF files, the method merges the generated GeoTIFF files into a single GeoTIFF file using GDAL.

    If the 'keep_individual_tiles' parameter is True, the individual tile files are kept. Otherwise, they are deleted.

    Finally, the method calls another method 'process_and_clip_raster' to process and clip the merged GeoTIFF file based on the provided geometry and MODIS NRT API parameters.
    """

    with self.out:
        bbox = self.get_bounding_box(distinct_values=distinct_values, feature=geometry)
        modis_nrt_params = self.gather_modis_nrt_parameters()

        if modis_nrt_params['create_sub_folder']:
            folder = f"{modis_nrt_params['folder_path']}/{str(datetime.datetime.now()).replace('-', '').replace('_', '').replace(':', '').replace('.', '')}/"
            os.mkdir(folder)

            modis_nrt_params['folder_path'] = folder
        tiles = modis_api.get_modis_tile(bbox)
        with self.out:
            self.out.clear_output()
            print(f'Processing tiles: {tiles}')
        matching_files = modis_api.get_modis_nrt_file_list(tiles, modis_nrt_params)

        hdf_files_to_process = []
        tif_list = []
        start=1
        for url in matching_files:
            modis_api.download_and_process_modis_nrt(url, modis_nrt_params['folder_path'], hdf_files_to_process, subdataset=self.modis_nrt_band_selection.value, tif_list=tif_list)
            start += 1

        merged_output = f'{folder}merged.tif'
        modis_api.merge_tifs(tif_list, merged_output)
        for file in tif_list + hdf_files_to_process:
            if modis_nrt_params['keep_individual_tiles']:
                pass
            else:
                try:
                    os.remove(file)
                except FileNotFoundError:
                    pass
        self.process_and_clip_raster(merged_output, geometry, modis_nrt_params)
        with self.out:
            self.out.clear_output()
            print('Processing Complete!')
        clipped_output = f'{folder}merged_clipped.tif'
        if modis_nrt_params['calculate_population']:
            with self.out:
                self.out.clear_output()
                pop_impacted = modis_api.calculate_population_in_flood_area(clipped_output)
                print(pop_impacted)


def gather_modis_nrt_parameters(self):
    """
    Gathers the parameters for the MODIS NRT processing.

    :return: A dictionary containing the gathered parameters:
             - 'date' or 'start_date' and 'end_date': The selected date(s) for processing.
             - 'multi_date': True if date range selected, False otherwise.
             - 'folder_path': The selected folder path where the output will be saved.
             - 'create_sub_folder': True if output should be saved in a sub-folder, False otherwise.
             - 'clip_to_geometry': True if the output should be clipped to a provided geometry, False otherwise.
             - 'keep_individual_tiles': True if individual tiles should be saved, False otherwise.
             - 'add_to_map': True if the processed image should be added to the map, False otherwise.
    """
    date_type = self.single_or_date_range_modis_nrt.value
    folder_path = self.filechooser.selected
    create_sub_folder = self.create_sub_folder.value
    clip_to_geometry = self.clip_to_geometry.value
    keep_individual_tiles = self.keep_individual_tiles.value
    add_image_to_map = self.add_image_to_map.value
    calculate_population = self.calculate_population.value
    if date_type == 'Single Date':
        date = self.date_picker_modis_nrt.value
        return {
            'date': date,
            'multi_date': False,
            'folder_path': folder_path,
            'create_sub_folder': create_sub_folder,
            'clip_to_geometry': clip_to_geometry,
            'keep_individual_tiles': keep_individual_tiles,
            'add_to_map': add_image_to_map,
            'calculate_population': calculate_population
        }
    elif date_type == 'Date Range':
        start_date = self.date_picker_modis_nrt.children[0].value
        end_date = self.date_picker_modis_nrt.children[1].value
        return {
            'start_date': start_date,
            'end_date': end_date,
            'multi_date': True,
            'folder_path': folder_path,
            'create_sub_folder': create_sub_folder,
            'clip_to_geometry': clip_to_geometry,
            'keep_individual_tiles': keep_individual_tiles,
            'add_to_map': add_image_to_map,
            'calculate_population': calculate_population
        }
    else:
        pass
