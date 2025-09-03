import dataclasses
import os
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape
from langgraph.prebuilt.chat_agent_executor import AgentState

from src.config.configuration import Configuration

env = Environment(
    loader=FileSystemLoader(os.path.dirname(__file__)),
    autoescape=select_autoescape(),
    trim_blocks=True,
    lstrip_blocks=True,
)


def apply_prompt_template(prompt_name: str, state: AgentState, configurable: Configuration = None) -> list:
    """
    将模板变量应用于提示模板并返回格式化消息。

    ### 参数
    - `prompt_name`: 要使用的提示模板的名称
    - `state`: 当前代理状态，包含需要替换的变量
    - `configurable`: 配置参数，用于自定义提示模板

    ### 返回

    - 一组消息，其中系统提示作为第一条消息
    :param prompt_name:
    :param state:
    :param configurable:
    :return:
    """
    state_vars = {
        "CURRENT_TIME": datetime.now().strftime("%a %b %d %Y %H:%M:%S %z"),
        **state,
    }

    if configurable:
        state_vars.update(dataclasses.asdict(configurable))

    try:
        template = env.get_template(f"{prompt_name}.md")
        system_prompt = template.render(**state_vars)
        return [{"role": "system", "content": system_prompt}] + state["messages"]
    except Exception as e:
        raise ValueError(f"应用提示词模板{prompt_name}错误: {e}")
