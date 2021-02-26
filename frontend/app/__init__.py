from flask import Flask
from flask_cors import CORS
from flask.logging import default_handler
import os
import logging
import sys
import time
from pythonjsonlogger import jsonlogger

from . import config

#from .legacy.routes import bp as api_legacy
from .v1.routes import bp as api_v1

class JsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        """Remap `log_record`s fields to fluentd-gcp counterparts."""
        super(JsonFormatter, self).add_fields(log_record, record, message_dict)
        log_record["time"] = log_record.get("time", log_record["asctime"])
        log_record["severity"] = log_record.get(
            "severity", log_record["levelname"])
        log_record["source"] = log_record.get("source", log_record["name"])
        del log_record["asctime"]
        del log_record["levelname"]
        del log_record["name"]


def create_app(test_config=None):
    app = Flask(__name__)
    CORS(app, expose_headers='WWW-Authenticate')

    configure_app(app)

    if test_config is not None:
        app.config.update(test_config)

    #app.register_blueprint(api_legacy)
    app.register_blueprint(api_v1)
    app.url_map.strict_slashes = False

    return app


def configure_app(app):
    # Load logging scheme from config.py
    app_settings = os.getenv('APP_SETTINGS')
    if not app_settings:
        app.config.from_object(config.BaseConfig)
    else:
        app.config.from_object(app_settings)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(app.config['LOGGING_LEVEL'])
    formatter = JsonFormatter(
        fmt=app.config['LOGGING_FORMAT'],
        datefmt=app.config['LOGGING_DATEFORMAT'])
    formatter.converter = time.gmtime
    handler.setFormatter(formatter)
    app.logger.removeHandler(default_handler)
    app.logger.addHandler(handler)
    app.logger.setLevel(app.config['LOGGING_LEVEL'])
    app.logger.propagate = False


