# config.py

import os
import yaml

class ConfigManager:
    _instance = None

    @classmethod
    def get_instance(cls, config_path=None):
        if cls._instance is None:
            if config_path is None:
                raise ValueError("A config path must be provided for the first instantiation.")
            cls._instance = cls(config_path)
        return cls._instance

    def __init__(self, config_path):
        if ConfigManager._instance is not None:
            raise Exception("This class is a singleton!")
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self):
        with open(self.config_path, 'r') as config_file:
            config = yaml.safe_load(config_file)
        return config

    def update_config(self, new_config):
        with open(self.config_path, 'w') as config_file:
            yaml.dump(new_config, config_file, default_flow_style=False)
        self.config = new_config

    @staticmethod
    def get_config_path():
        # Adjust the folder and file names as necessary
        package_dir = os.path.dirname(__file__)
        return os.path.join(package_dir, 'config.yaml')

