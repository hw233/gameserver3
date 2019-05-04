# -*- coding: utf-8 -*-
__author__ = 'Administrator'

from config import var

class WebConfig(object):
    """Base config class."""
    pass

class ProdConfig(WebConfig):
    """Production config class."""
    pass

class DevConfig(WebConfig):
    """Development config class."""
    # Open the DEBUG
    DEBUG = True
    HOST=var.WEB_HOST
    PORT=var.WEB_PORT
    UPLOAD_FOLDER = '/web/static'

    MAX_CONTENT_LENGTH = 30 * 1024 * 1024
