import json
import os


class SettingsMarshaller:
    def __init__(self):
        self.settings_file_name = 'settings.json'

        self.settings = Settings()
        if os.path.isfile(self.settings_file_name):
            with open(self.settings_file_name, 'r') as settings_file:
                self.settings.load(json.load(settings_file))

    def save(self):
        with open(self.settings_file_name, 'w') as settings_file:
            json.dump(self.settings.__dict__, settings_file)

    def default_if_none(self, millie_property, default):
        value = getattr(self.settings, millie_property)
        if value is None:
            value = default
            setattr(self.settings, millie_property, value)
        return value


class Settings:
    def __init__(self):
        self.showing_background_image = None
        self.background_image_height = None
        self.background_image_width = None
        self.left_pad = None
        self.top_pad = None
        self.showing_face_rectangles = None
        self.recognition_threshold = None
        self.use_webcam = None
        self.default_height = None
        self.default_width = None

    def load(self, data):
        self.__dict__ = data
