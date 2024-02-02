# File: mcimageprocessing/__init__.py

"""Top-level package for mcimageprocessing."""

__author__ = """Nicholas Dowhaniuk"""
__email__ = 'nick@kndconsulting.org'
__version__ = '0.1.0'

import os
from .config.config import ConfigManager

# Use the get_config_path method to get the correct config path
config_path = ConfigManager.get_config_path()

# Initialize the ConfigManager with the path to the config.yaml
config_manager = ConfigManager.get_instance(config_path)

# Import the jupyter module to make it available as mcimageprocessing.jupyter
from . import jupyter

# You can define __all__ to specify what is imported with "from mcimageprocessing import *"
__all__ = ['jupyter']
