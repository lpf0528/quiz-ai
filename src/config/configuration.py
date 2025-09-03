import os
from dataclasses import dataclass, fields
from typing import Any, Optional

from langchain_core.runnables import RunnableConfig

from src.config.report_style import ReportStyle


@dataclass(kw_only=True)
class Configuration:
    # resources: list[Resource] = field(
    #     default_factory=list
    # )  # Resources to be used for the research
    max_plan_iterations: int = 1  # Maximum number of plan iterations
    max_step_num: int = 3  # Maximum number of steps in a plan
    max_search_results: int = 3  # Maximum number of search results
    mcp_settings: dict = None  # MCP settings, including dynamic loaded tools
    report_style: str = ReportStyle.ACADEMIC.value  # Report style
    enable_deep_thinking: bool = False  # Whether to enable deep thinking

    @classmethod
    def from_runnable_config(cls, config: Optional[RunnableConfig] = None):
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )
        values: dict[str, Any] = {
            # 如果环境变量中没有相应的值，则从 configurable 字典中获取值。
            f.name: os.environ.get(f.name.upper(), configurable.get(f.name))
            for f in fields(cls)
            if f.init  # 仅为那些在类实例化时需要初始化的字段获取值（即，init=True 的字段）。
        }
        return cls(**{k: v for k, v in values.items() if v is not None})
