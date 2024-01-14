import os
import re

import requests
from bs4 import BeautifulSoup
from osgeo import gdal

from mcimageprocessing.simplified.widget_creation_components.gee import *


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
        self.date_picker_modis_nrt = DatePicker(
            description='Select Date:',
            disabled=False,
            value=max(self.modis_nrt_available_dates),  # Default value
            min=min(self.modis_nrt_available_dates),  # Minimum value
            max=max(self.modis_nrt_available_dates)  # Maximum value (assumes 31 days in max month)
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

    self.modis_nrt_available_dates = self.get_modis_nrt_dates()

    self.single_or_date_range_modis_nrt = widgets.ToggleButtons(
        options=['Single Date', 'Date Range', 'All Available Images'],
        disabled=False,
        value='Single Date',
        tooltips=['Single Date', 'Date Range', 'All Available Images'],
    )

    self.modis_nrt_date_vbox = VBox([])
    self.on_single_or_date_range_change_modis_nrt({'new': self.single_or_date_range_modis_nrt.value})

    self.single_or_date_range_modis_nrt.observe(
        lambda change: self.on_single_or_date_range_change_modis_nrt(change),
        names='value'
    )

    self.end_of_vbox_items = widgets.Accordion([widgets.TwoByTwoLayout(
        top_left=self.create_sub_folder,
        top_right=self.clip_to_geometry,
        bottom_left=self.keep_individual_tiles,
        bottom_right=self.add_image_to_map
    )])

    self.end_of_vbox_items.set_title(0, 'Options')

    # Return a list of widgets
    return [self.single_or_date_range_modis_nrt, self.modis_nrt_date_vbox, self.filechooser,
            self.end_of_vbox_items]

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
    bbox = self.get_bounding_box(distinct_values=distinct_values, feature=geometry)
    modis_nrt_params = self.gather_modis_nrt_parameters()
    with self.out:
        print(modis_nrt_params)
    if modis_nrt_params['create_sub_folder']:
        folder = f"{modis_nrt_params['folder_path']}/{str(datetime.datetime.now()).replace('-', '').replace('_', '').replace(':', '').replace('.', '')}/"
        os.mkdir(folder)

        modis_nrt_params['folder_path'] = folder
    tiles = self.get_modis_tile(bbox)
    with self.out:
        print(f'Processing tiles: {tiles}')
    matching_files = []
    for tile in tiles:
        h = f"{tile[0]:02d}"
        v = f"{tile[1]:02d}"
        year = modis_nrt_params['date'].year
        doy = f"{modis_nrt_params['date'].timetuple().tm_yday:03d}"
        base_url_folder = f"{self.modis_nrt_api_root_url}{year}/{doy}/"
        file_pattern = rf"MCDWD_L3_NRT\.A{year}{doy}\.h{h}v{v}\.061\.\d+\.hdf"

        response = requests.get(base_url_folder)
        html_content = response.text

        soup = BeautifulSoup(html_content, 'html.parser')

        links = soup.find_all('a')

        # Check if the request was successful
        for link in links:
            href = link.get('href')
            if re.search(file_pattern, href):
                matching_files.append(href)

    headers = {
        'Authorization': f'Bearer {self.modis_download_token}'
    }
    hdf_files_to_process = []
    tif_list = []
    for url in matching_files:
        response = requests.get(url, headers=headers, stream=True)
        if response.status_code == 200:
            filename = f"{modis_nrt_params['folder_path']}{url.split('/')[-1]}"  # Extracts the filename
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            hdf_files_to_process.append(filename)
            datasets = []
            subdataset_index = 0
            for hdf_file in hdf_files_to_process:
                # Open the HDF file
                hdf_dataset = gdal.Open(hdf_file, gdal.GA_ReadOnly)
                subdatasets = hdf_dataset.GetSubDatasets()

            for hdf_file in hdf_files_to_process:
                hdf_dataset = gdal.Open(hdf_file, gdal.GA_ReadOnly)
                subdatasets = hdf_dataset.GetSubDatasets()

                # Select a subdataset
                subdataset = subdatasets[subdataset_index][0]

                # Open the subdataset
                ds = gdal.Open(subdataset, gdal.GA_ReadOnly)

                # Define output path for the GeoTIFF
                output_tiff = hdf_file.replace('.hdf', '.tif')

                tif_list.append(output_tiff)

                # Convert to GeoTIFF
                gdal.Translate(output_tiff, ds)

                # Close the dataset
                ds = None

    else:
        print(f"Failed to download {url}. Status code: {response.status_code}")

    merged_output = f'{folder}merged.tif'
    gdal.Warp(merged_output, tif_list)
    for file in tif_list + hdf_files_to_process:
        if modis_nrt_params['keep_individual_tiles']:
            pass
        else:
            try:
                os.remove(file)
            except FileNotFoundError:
                pass
    self.process_and_clip_raster(merged_output, geometry, modis_nrt_params)

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
    if date_type == 'Single Date':
        date = self.date_picker_modis_nrt.value
        return {
            'date': date,
            'multi_date': False,
            'folder_path': folder_path,
            'create_sub_folder': create_sub_folder,
            'clip_to_geometry': clip_to_geometry,
            'keep_individual_tiles': keep_individual_tiles,
            'add_to_map': add_image_to_map
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
            'add_to_map': add_image_to_map
        }
    pass
