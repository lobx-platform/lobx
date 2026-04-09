import asyncio
import functools
import json
import logging
import os
from datetime import datetime
from enum import Enum
from json import JSONEncoder
from types import SimpleNamespace
from uuid import UUID

import yaml
from pydantic import BaseModel
from termcolor import colored

CUR_LEVEL = logging.CRITICAL

dict_keys = type({}.keys())
dict_values = type({}.values())

class CustomFormatter(logging.Formatter):
    COLORS = {
        "WARNING": "yellow",
        "INFO": "cyan",
        "DEBUG": "blue",
        "CRITICAL": "red",
        "ERROR": "red",
    }

    def format(self, record):
        log_message = super(CustomFormatter, self).format(record)
        return colored(log_message, self.COLORS.get(record.levelname))

def setup_trading_logger(market_id: str) -> logging.Logger:
    logger = logging.getLogger(f"trading_market_{market_id}")
    logger.setLevel(logging.INFO)

    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{market_id}.log")

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger

def setup_custom_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(CUR_LEVEL)

    # Only create a stream handler
    ch = logging.StreamHandler()
    ch.setLevel(CUR_LEVEL)

    formatter = CustomFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)

    logger.addHandler(ch)

    return logger

def load_config() -> SimpleNamespace:
    with open("config/app.yaml", "r", encoding="utf-8") as file:
        config_data = yaml.safe_load(file)
    return SimpleNamespace(**config_data)

# YAML constructor for !python/tuple
def tuple_constructor(loader, node):
    return tuple(loader.construct_sequence(node))

yaml.SafeLoader.add_constructor("!python/tuple", tuple_constructor)


logger = setup_custom_logger(__name__)
CONFIG = load_config()


class CustomEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (UUID, Enum)):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, BaseModel):
            return obj.model_dump()
        if isinstance(obj, (dict_keys, dict_values)):
            return list(obj)
        return JSONEncoder.default(self, obj)