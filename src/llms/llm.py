import os
from pathlib import Path
from typing import Dict, Any

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_deepseek import ChatDeepSeek
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from src.config.agents import LLMType
from src.config.loader import load_yaml_config
from src.llms.providers.dashscope import ChatDashscope

_llm_cache: dict[LLMType, BaseChatModel] = {}


def _get_config_file_path() -> str:
    """Get the path to the configuration file."""
    return str((Path(__file__).parent.parent.parent / "conf.yaml").resolve())


def get_llm_by_type(llm_type: LLMType):
    # 从缓存中获取LLM实例
    if llm_type in _llm_cache:
        return _llm_cache[llm_type]

    # 从配置文件中获取LLM配置
    conf = load_yaml_config(_get_config_file_path())
    # 使用配置创建LLM实例
    llm = _create_llm_use_conf(llm_type, conf)
    # 缓存LLM实例
    _llm_cache[llm_type] = llm
    return llm


def _get_llm_type_config_keys() -> dict[str, str]:
    """Get mapping of LLM types to their configuration keys."""
    return {
        "reasoning": "REASONING_MODEL",
        "basic": "BASIC_MODEL",
        "vision": "VISION_MODEL",
        "code": "CODE_MODEL",
    }


def _get_env_llm_conf(llm_type: str) -> Dict[str, Any]:
    """
    Get LLM configuration from environment variables.
    Environment variables should follow the format: {LLM_TYPE}__{KEY}
    e.g., BASIC_MODEL__api_key, BASIC_MODEL__base_url
    """
    prefix = f"{llm_type.upper()}_MODEL__"
    conf = {}
    for key, value in os.environ.items():
        if key.startswith(prefix):
            conf_key = key[len(prefix):].lower()
            conf[conf_key] = value
    return conf


def _create_llm_use_conf(llm_type: LLMType, conf: Dict[str, Any]) -> BaseChatModel:
    """使用配置创建LLM实例"""
    # 获取LLM类型对应的配置键
    llm_type_config_keys = _get_llm_type_config_keys()
    config_key = llm_type_config_keys.get(llm_type)

    if not config_key:
        raise ValueError(f"Unknown LLM type: {llm_type}")

    # 获取LLM类型对应的配置-》 BASIC_MODEL
    llm_conf = conf.get(config_key, {})
    if not isinstance(llm_conf, dict):
        raise ValueError(f"Invalid LLM configuration for {llm_type}: {llm_conf}")

    # 获取环境变量中的配置：BASIC_MODEL__api_key
    env_conf = _get_env_llm_conf(llm_type)

    # 合并配置，环境变量配置优先
    merged_conf = {**llm_conf, **env_conf}

    if not merged_conf:
        raise ValueError(f"No configuration found for LLM type: {llm_type}")

    # 增加max_retries 重试次数
    if "max_retries" not in merged_conf:
        merged_conf["max_retries"] = 3

    # 处理SSL验证设置
    verify_ssl = merged_conf.pop("verify_ssl", True)

    # Create custom HTTP client if SSL verification is disabled
    if not verify_ssl:
        http_client = httpx.Client(verify=False)
        http_async_client = httpx.AsyncClient(verify=False)
        merged_conf["http_client"] = http_client
        merged_conf["http_async_client"] = http_async_client

    if "azure_endpoint" in merged_conf or os.getenv("AZURE_OPENAI_ENDPOINT"):
        return AzureChatOpenAI(**merged_conf)

    # Check if base_url is dashscope endpoint
    if "base_url" in merged_conf and "dashscope." in merged_conf["base_url"]:
        if llm_type == "reasoning":
            merged_conf["extra_body"] = {"enable_thinking": True}
        else:
            merged_conf["extra_body"] = {"enable_thinking": False}
        return ChatDashscope(**merged_conf)

    if llm_type == "reasoning":
        merged_conf["api_base"] = merged_conf.pop("base_url", None)
        return ChatDeepSeek(**merged_conf)
    else:
        return ChatOpenAI(**merged_conf)
