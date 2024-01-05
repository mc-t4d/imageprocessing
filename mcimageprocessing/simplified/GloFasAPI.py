import cdsapi
import os
from mcimageprocessing.simplified.MappingSetup import JupyterAPI

class GlofasAPI:
    def __init__(self):
        self.client = cdsapi.Client()

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
