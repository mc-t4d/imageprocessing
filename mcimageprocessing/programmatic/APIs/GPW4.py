import ipywidgets as widgets
from ipywidgets import Layout
import ee
from mcimageprocessing.programmatic.APIs.EarthEngine import EarthEngineManager
from mcimageprocessing.programmatic.shared_functions.shared_utils import mosaic_images
import pkg_resources
import datetime
from typing import Any, Dict, List
import os
import rasterio
from rasterio.merge import merge
from geojson import Feature, FeatureCollection
from concurrent.futures import ThreadPoolExecutor, as_completed

class GP4W:
    """
    WorldPop class

    A class for processing WorldPop data using the WorldPop API or Google Earth Engine.

    Attributes:
    - worldpop_agesex_bands (list): List of age and sex bands for WorldPop data.
    - ee_auth_path (str): Path to the authentication file for Google Earth Engine.
    - ee_instance (EarthEngineManager): Instance of the EarthEngineManager class for managing interactions with Google Earth Engine.

    Methods:
    - __init__(): Initializes the class with default values.
    - process_residential_population(geometry, worldpop_params): Process Residential Population data.
    - mosaic_images(file_names, output_filename): Mosaic images and save as a single file.
    - download_and_process_image(image, geometry, scale, worldpop_params, band): Download and process the image.
    - process_age_and_sex_structures(geometry, worldpop_params): Process Age and Sex Structures data.
    - get_image_dates(): Get the dates of the WorldPop population data.
    - validate_parameters(worldpop_params): Validate the parameters.
    - process_worldpop_api(geometry, distinct_values, index, worldpop_params=None): Method to process WorldPop API data for given parameters.
    """

    def __init__(self):

        self.ee_instance = EarthEngineManager()

    def process_population_count(self, geometry: Any, worldpop_params: Dict[str, Any]) -> Any:
        """
        Process residential population based on the given parameters.

        :param geometry: The geometry to apply the process on.
        :type geometry: Any
        :param worldpop_params: The parameters needed for the WorldPop processing.
        :type worldpop_params: Dict[str, Any]
        :return: The processed image if statistics_only is not True, otherwise the calculated statistics.
        :rtype: Any
        """

        if worldpop_params['statistics_only']:
            all_stats = ee.Dictionary()

        band = 'population'
        image, geometry, scale = self.ee_instance.get_image(
            multi_date=True,
            start_date=f'{worldpop_params["year"]}-01-01',
            end_date=f'{worldpop_params["year"]}-12-31',
            image_collection='WorldPop/GP/100m/pop',
            band=band,
            geometry=geometry,
            aggregation_method='max')

        geojson = geometry.getInfo()
        multipolygon_feature = Feature(geometry=geojson)

        feature_collection = FeatureCollection([multipolygon_feature])



        if worldpop_params['statistics_only']:
            stats = self.ee_instance.calculate_statistics(image, geometry, band)
            all_stats = all_stats.set(band, stats)
            all_stats_info = all_stats.getInfo()
            return all_stats_info

        self.download_and_process_image(image, geometry, scale, worldpop_params, band)
        return image

    def mosaic_images(self, file_names: List[str], output_filename: str = 'mosaic.tif') -> None:
        """
        Merges multiple raster images into a single mosaic image.

        :param file_names: List of file names of raster images to be merged.
        :param output_filename: Output file name for the mosaic image. Defaults to 'mosaic.tif'.

        :return: None

        """
        src_files_to_mosaic = []
        for fn in file_names:
            src = rasterio.open(fn)
            src_files_to_mosaic.append(src)

        mosaic, out_trans = merge(src_files_to_mosaic)
        out_meta = src.meta.copy()
        out_meta.update({"driver": "GTiff",
                         "height": mosaic.shape[1],
                         "width": mosaic.shape[2],
                         "transform": out_trans})

        with rasterio.open(f"{output_filename}", "w", **out_meta) as dest:
            dest.write(mosaic)

        for fn in file_names:
            os.remove(fn)

    def download_and_process_image(self, image: ee.Image, geometry: Any, scale: Any, worldpop_params: Dict[str, Any],
                                   band: str) -> None:
        """
        Downloads and processes an image.

        :param image: The Earth Engine image to download.
        :param geometry: The geometry to clip the image to.
        :param scale: The scale of the image to download.
        :param worldpop_params: Additional parameters for WorldPop.
        :param band: The band of the image to download.
        :return: None
        """
        file_names, download_successful = self.ee_instance.download_and_split(image, geometry, scale,
                                                                  params=worldpop_params,
                                                                  band=band)

        if not download_successful:
            output_filename = f"mosaic_{band}.tif"
            output_filename = f"{worldpop_params['folder_output']}/{output_filename}"
            mosaic_images(file_names, output_filename)
        else:
            print(f"Downloaded {file_names[0]} successfully without needing to mosaic.")

    def process_age_and_sex_structures(self, geometry, worldpop_params):
        all_stats = {}

        def process_band(geometry, band):
            image, geometry, scale = self.ee_instance.get_image(
                multi_date=True,
                start_date='2020-01-01',
                end_date='2020-12-31',
                image_collection='WorldPop/GP/100m/pop_age_sex_cons_unadj',
                band=band,
                geometry=geometry,
                aggregation_method='max')

            if worldpop_params['statistics_only']:
                stats_info = self.ee_instance.calculate_statistics(image, geometry, band)
                return band, stats_info
            else:
                self.download_and_process_image(image, geometry, scale, worldpop_params, band)
                return band, None  # Or appropriate response

        if worldpop_params['statistics_only']:
            with ThreadPoolExecutor() as executor:
                futures = {executor.submit(process_band, geometry, band): band for band in self.worldpop_agesex_bands}
                for future in as_completed(futures):
                    band, stats_info = future.result()
                    all_stats[band] = stats_info

            return fetch_stats(all_stats)  # Assuming fetch_stats is defined as before
        else:
            with ThreadPoolExecutor() as executor:
                for band in self.worldpop_agesex_bands:
                    executor.submit(process_band, geometry, band)
            return None  # Or

    def get_image_dates(self) -> List[datetime.datetime]:
        """
        Returns the dates of the images in the given image collection.

        :return: A list of dates representing the dates of the images in the image collection.
        """
        # Get the image collection
        image_collection = self.ee_instance.get_image_collection_dates("WorldPop/POP")

        # Get the dates
        dates = self.ee_instance.get_image_dates(image_collection)

        return dates

    def validate_parameters(self, worldpop_params: Dict[str, Any]) -> bool:
        """
        Validates the parameters for the worldpop_params.

        :param worldpop_params: A dictionary containing the worldpop parameters.
                                It should have the following keys:
                                - folder_output: The output folder path.
                                - api_source: The API source (either 'WorldPop' or 'Google Earth Engine').
                                - year: The year.
                                - datatype: The data type.

        :return: True if all parameters are valid, False otherwise.
        """
        if not worldpop_params['folder_output']:
            print("Please select an output folder.")
            return False

        if not os.path.exists(worldpop_params['folder_output']):
            print("The selected output folder does not exist.")
            return False

        if not worldpop_params['api_source'] in ['WorldPop', 'Google Earth Engine']:
            print("Please select a valid API source.")
            return False

        if not worldpop_params['year']:
            print("Please select a valid year.")
            return False

        if not worldpop_params['datatype']:
            print("Please select a valid data type.")
            return False

        return True

    def process_worldpop_api(self, geometry: Any, distinct_values: Any, index: Any,
                             worldpop_params: Dict[str, Any] = None) -> Any:
        """
        :param geometry: The geometry for which to process the WorldPop API data.
        :param distinct_values: A dictionary of distinct values to filter the WorldPop data by.
        :param index: The index to retrieve from the filtered WorldPop data.
        :param worldpop_params: Optional parameters for the WorldPop API request.
        :return: The processed WorldPop data or a message indicating no valid data type provided.

        This method processes the WorldPop API data based on the given parameters. It validates the parameters, creates a sub-folder if required, ensures the geometry is in the correct format
        *, and then processes the data based on the requested data type.

        If the 'datatype' parameter in 'worldpop_params' is set to 'Residential Population', it calls the 'process_residential_population' method and returns the processed image. If the 'statistics
        *_only' parameter in 'worldpop_params' is set to True, it also saves the statistics as a JSON file in the folder output.

        If the 'datatype' parameter in 'worldpop_params' is set to 'Age and Sex Structures', it calls the 'process_age_and_sex_structures' method and returns the processed statistics. If the
        * 'statistics_only' parameter in 'worldpop_params' is set to True, it also saves the statistics as a JSON file in the folder output.

        If 'worldpop_params' is not provided or if no valid 'datatype' value is provided, it returns a message indicating no valid data type provided.

        If no valid 'worldpop_params' value is provided, it prints a message indicating so.
        """

        print(worldpop_params)

        if not self.validate_parameters(worldpop_params):
            return

        if worldpop_params['create_sub_folder']:
            worldpop_params['folder_output'] = f"{worldpop_params['folder_output']}/{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.mkdir(worldpop_params['folder_output'])

        geometry = self.ee_instance.ee_ensure_geometry(geometry)

        if worldpop_params and 'datatype' in worldpop_params:
            if worldpop_params['datatype'] == 'Residential Population':
                image = self.process_residential_population(geometry, worldpop_params)
                if worldpop_params['statistics_only']:
                    with open(f"{worldpop_params['folder_output']}/statistics.json", 'w') as f:
                        f.write(str(image))
                    return image
                return image

            elif worldpop_params['datatype'] == 'Age and Sex Structures':
                statistics = self.process_age_and_sex_structures(geometry, worldpop_params)
                if worldpop_params['statistics_only']:
                    with open(f"{worldpop_params['folder_output']}/statistics.json", 'w') as f:
                        f.write(str(statistics))

                    print(statistics)
                    return statistics
                else:
                    return statistics

            else:
                return 'No valid data type provided.'


        else:
            print("No valid worldpop_params provided.")


