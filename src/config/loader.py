import os
from typing import Dict, Any

import yaml

_config_cache: Dict[str, Dict[str, Any]] = {}


def replace_env_vars(value: str) -> str:
    if not isinstance(value, str):
        return value
    if value.startswith("$"):
        env_var = value[1:]
        return os.getenv(env_var, env_var)
    return value


def process_dict(config: Dict[str, Any]) -> Dict[str, Any]:
    if not config:
        return {}
    result = {}
    for k, v in config.items():
        if isinstance(v, dict):
            result[k] = process_dict(v)
        elif isinstance(v, str):
            result[k] = replace_env_vars(v)
        else:
            result[k] = v
    return result


def load_yaml_config(filth_path: str) -> Dict[str, Any]:
    """加载yaml配置文件"""
    if not os.path.exists(filth_path):
        raise {}
    if filth_path in _config_cache:
        return _config_cache[filth_path]

    with open(filth_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    processed_config = process_dict(config)

    _config_cache[filth_path] = processed_config
    return processed_config
