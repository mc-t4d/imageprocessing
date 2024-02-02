# File: mcimageprocessing/__init__.py

"""Top-level package for mcimageprocessing."""

__author__ = """Nicholas Dowhaniuk"""
__email__ = 'nick@kndconsulting.org'
__version__ = '0.1.0'

import os
from .config.config import ConfigManager

# Construct the path to the config.yaml file
config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')

# Initialize the ConfigManager with the path to the config.yaml
config_manager = ConfigManager.get_instance(config_path)

# Import the jupyter module to make it available as mcimageprocessing.jupyter
from . import jupyter

# You can define __all__ to specify what is imported with "from mcimageprocessing import *"
__all__ = ['jupyter']
