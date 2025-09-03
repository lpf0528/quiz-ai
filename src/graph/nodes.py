import json
import logging
from typing import Annotated, Literal

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.types import Command, interrupt

from src.config.agents import AGENT_LLM_MAP
from src.config.configuration import Configuration
from src.config.tools import SELECTED_SEARCH_ENGINE, SearchEngine

from src.graph.types import State
from src.llms.llm import get_llm_by_type
from src.prompts.planner_model import Plan, StepType
from src.prompts.template import apply_prompt_template
from src.tools.search import LoggedTavilySearch, get_web_search_tool
from src.utils.json_utils import repair_json_output

logger = logging.getLogger(__name__)


@tool
def handoff_to_planner(
        research_topic: Annotated[str, "The topic of the research task to be handed off."],
        locale: Annotated[str, "The user's detected language locale (e.g., en-US, zh-CN)."],
):
    """将任务移交给规划者代理进行计划。"""
    # 这个工具不会返回任何内容：我们只是用它来表示需要将任务移交给规划者代理
    return


def research_team_node(state: State):
    """研究团队节点：执行计划的专业智能体集合：。
        研究员：使用网络搜索引擎、爬虫甚至 MCP 服务等工具进行网络搜索和信息收集。
        编码员：使用 Python REPL 工具处理代码分析、执行和技术任务。 每个智能体都可以访问针对其角色优化的特定工具，并在 LangGraph 框架内运行
    """
    logger.info("研究团队正在协同处理任务。")
    pass


def researcher_node(state: State):
    """研究节点：使用网络搜索引擎、爬虫甚至 MCP 服务等工具进行网络搜索和信息收集。"""
    logger.info("研究员节点 开始.")
    pass


# def reporter_node(state: State, config: RunnableConfig):
#     """
#     报告员：研究输出的最终阶段处理器
#         汇总研究团队的发现
#         处理和组织收集的信息
#         生成全面的研究报告
#     """
#     logger.info("报告节点 开始.")
#     configurable = Configuration.from_runnable_config(config)
#     current_plan = state.get('current_plan', '')
#
#     _input = {
#         'messages': [
#             HumanMessage(
#                 f"# Research Requirements\n\n## Task\n\n{current_plan.title}\n\n## Description\n\n{current_plan.thought}")
#         ],
#         "locale": state.get("locale", "en-US"),
#     }
#     invoke_messages = apply_prompt_template('reporter', _input, configurable)
#     # 观察
#     observations = state.get('observations', [])
#     """
#     重要提示：根据提示中的格式编写报告。记得包括：
#     1. 关键点 - 用项目符号列出最重要的发现
#     2. 概述 - 简要介绍主题
#     3. 详细分析 - 按逻辑分段组织
#     4. 调查说明（可选） - 适用于更全面的报告
#     5. 主要参考文献 - 在最后列出所有引用
#
#     对于引用，不要在正文中添加内嵌引用。相反，请在最后的“主要参考文献”部分列出所有引用，格式为：`- [来源标题](URL)`。引用之间空一行以提高可读性。
#
#     优先使用Markdown表格进行数据展示和比较。每当展示比较数据、统计数据、功能或选项时，使用表格。结构化表格要有清晰的标题和对齐的列。示例表格格式：
#
#     | 功能     | 描述        | 优点   | 缺点   |
#     |----------|-------------|--------|--------|
#     | 功能 1   | 描述 1      | 优点 1 | 缺点 1 |
#     | 功能 2   | 描述 2      | 优点 2 | 缺点 2 |
#     """
#
#     invoke_messages.append(HumanMessage(
#         content="IMPORTANT: Structure your report according to the format in the prompt. Remember to include:\n\n1. Key Points - A bulleted list of the most important findings\n2. Overview - A brief introduction to the topic\n3. Detailed Analysis - Organized into logical sections\n4. Survey Note (optional) - For more comprehensive reports\n5. Key Citations - List all references at the end\n\nFor citations, DO NOT include inline citations in the text. Instead, place all citations in the 'Key Citations' section at the end using the format: `- [Source Title](URL)`. Include an empty line between each citation for better readability.\n\nPRIORITIZE USING MARKDOWN TABLES for data presentation and comparison. Use tables whenever presenting comparative data, statistics, features, or options. Structure tables with clear headers and aligned columns. Example table format:\n\n| Feature | Description | Pros | Cons |\n|---------|-------------|------|------|\n| Feature 1 | Description 1 | Pros 1 | Cons 1 |\n| Feature 2 | Description 2 | Pros 2 | Cons 2 |",
#         name="system"
#     ))
#     for observation in observations:
#         invoke_messages.append(HumanMessage(content=observation, name="observation"))


def human_feedback_node(state: State, config: RunnableConfig):
    # -> Command[Literal["planner", "research_team", "reporter", "__end__"]]
    """
    人类反馈节点：用于接收用户反馈并更新状态"""
    logger.info("人类反馈节点 开始.")
    current_plan = state.get('current_plan', '')
    auto_accepted_plan = state.get("auto_accepted_plan", False)
    if auto_accepted_plan:
        feedback = interrupt("请审阅该计划。")
        logger.info(f"人类反馈节点 收到反馈: {feedback}")
        if feedback and str(feedback).upper().startswith("[EDIT_PLAN]"):
            # 如果反馈未被接受，并编辑了计划，则返回计划节点。
            return Command(update={"messages": [HumanMessage(content=feedback, name="feedback")]}, goto="planner")
        elif feedback and str(feedback).upper().startswith("[ACCEPTED]"):
            logger.info("人类反馈节点 计划已被接受.")
        else:
            raise TypeError(f"人类反馈节点 未知反馈类型: {feedback}")

    # 计划的迭代次数
    plan_iterations = state.get('plan_iterations', 0)
    goto = "research_team"
    try:
        current_plan = repair_json_output(current_plan)
        plan_iterations += 1
        new_plan = json.loads(current_plan)
    except Exception as e:
        logger.error(f"人类反馈节点 未知反馈类型: {e}")
        if plan_iterations > 1:
            # 计划的迭代次数超过1次，返回报告节点
            return Command(goto="reporter")
        else:
            # 计划的迭代次数未超过1次，返回结束节点
            return Command(goto="__end__")

    return Command(update={"current_plan": Plan.model_validate(new_plan),
                           "plan_iterations": plan_iterations,
                           "locale": new_plan["locale"], }, goto=goto)


def planner_node(state: State, config: RunnableConfig):
    # -> Command[Literal["human_feedback", "reporter"]]:
    """规划器：负责任务分解和规划的战略组件
    分析研究目标并创建结构化执行计划
    确定是否有足够的上下文或是否需要更多研究
    管理研究流程并决定何时生成最终报告
    """
    logger.info("规划器 开始.")
    configurable = Configuration.from_runnable_config(config)
    # 计划迭代次数
    plan_iterations = state["plan_iterations"] if state.get("plan_iterations", 0) else 0
    messages = apply_prompt_template("planner", state, configurable)
    if state.get("enable_background_investigation", False) and state.get('background_investigation_results'):
        logger.info("规划器 开启背景调查，且存在背景调查结果.")
        # 是否开启背景调查，背景调查结果
        messages += [{
            "role": "user",
            "content": (
                    "background investigation results of user query:\n"
                    + state["background_investigation_results"]
                    + "\n"
            ),
        }]
    if configurable.enable_deep_thinking:
        # 是否开启深度思考
        logger.info("规划器 开启深度思考.")
        llm = get_llm_by_type('reasoning')
    elif AGENT_LLM_MAP["planner"] == "basic":
        # 结构化输出
        llm = get_llm_by_type("basic").with_structured_output(
            Plan,
            # method="json_mode",
        )
    else:
        llm = get_llm_by_type(AGENT_LLM_MAP["planner"])

    if plan_iterations >= configurable.max_plan_iterations:
        logger.info("规划器 达到最大迭代次数-> reporter.")
        return Command(goto='reporter')

    full_response = ""
    if AGENT_LLM_MAP["planner"] == "basic" and not configurable.enable_deep_thinking:
        # 非深度思考
        response = llm.invoke(messages)
        full_response = response.model_dump_json(indent=4, exclude_none=True)
    else:
        # 深度思考
        response = llm.stream(messages)
        for chunk in response:
            full_response += chunk.content
    logger.info(f"规划器 响应: {full_response}")

    try:
        # 解析规划器响应
        curr_plan = json.loads(repair_json_output(full_response))
    except json.JSONDecodeError as e:
        if plan_iterations > 0:
            logger.warning(f"规划器 解析响应失败 结束, 跳转: reporter: {e}")
            return Command(goto="reporter")
        else:
            logger.warning(f"规划器 解析响应失败 结束, 跳转: __end__: {e}")
            return Command(goto="__end__")
    # 检查规划器响应是否包含足够的上下文
    if isinstance(curr_plan, dict) and curr_plan.get("has_enough_context"):
        new_plan = Plan.model_validate(curr_plan)
        logger.info(f"规划器 响应包含足够的上下文 结束. 跳转: reporter")
        return Command(
            update={
                "messages": [AIMessage(content=full_response, name="planner")],
                "current_plan": new_plan,
            },
            goto="reporter",
        )
    logger.info(f"协调器 结束. 跳转: human_feedback")
    return Command(update={
        "messages": [AIMessage(content=full_response, name="planner")],
        "current_plan": full_response,
    }, goto="human_feedback")


def background_investigation_node(state: State, config: RunnableConfig):
    """背景调查节点：负责在研究开始前进行背景调查，收集相关信息和背景知识。"""
    logger.info("背景调查节点 开始.")
    configurable = Configuration.from_runnable_config(config)
    query = state.get("research_topic")  # 什么是langchain
    background_investigation_results = None
    # 背景调查
    if SELECTED_SEARCH_ENGINE == SearchEngine.TAVILY.value:
        searched_content = LoggedTavilySearch(
            max_results=configurable.max_search_results,
            topic="general",
            include_answer=True,
            include_raw_content=True,
            include_images=True,
            include_image_descriptions=True,
        ).invoke(query)
        logger.info(f"背景调查节点 搜索结果: {json.dumps(searched_content, ensure_ascii=False)}")
        if isinstance(searched_content, list):
            background_investigation_results = [
                f"## {item.get('title', '')}\n\n{item.get('content', '')}" for item in searched_content
            ]
            return {
                'background_investigation_results': '\n\n'.join(background_investigation_results)
            }
        else:
            logger.error(f"背景调查节点 搜索失败: {searched_content}")
    else:
        background_investigation_results = get_web_search_tool(
            configurable.max_search_results
        ).invoke(query)
    return {
        'background_investigation_results': json.dumps(
            background_investigation_results, ensure_ascii=False
        )
    }


def coordinator_node(state: State, config: RunnableConfig) -> Command[
    Literal["planner", 'background_investigator', "__end__"]]:
    """
    协调器：管理工作流生命周期的入口点
    1、根据用户输入启动研究过程
    2、在适当时候将任务委派给规划器
    3、作为用户和系统之间的主要接口
    :return:
    """
    logger.info("协调器 开始.")
    configurable = Configuration.from_runnable_config(config)
    messages = apply_prompt_template("coordinator", state)

    response = get_llm_by_type(AGENT_LLM_MAP["coordinator"]).bind_tools([handoff_to_planner]).invoke(messages)
    logger.info(f"协调器 响应: {response}")

    goto = "__end__"
    locale = state.get("locale", "en-US")
    research_topic = state.get("research_topic", '')
    if len(response.tool_calls) > 0:
        # 存在工具的调用
        goto = "planner"
        if state.get("enable_background_investigation", False):
            # 背景调查
            goto = "background_investigator"
        try:
            for tool_call in response.tool_calls:
                if tool_call.get('name', '') != "handoff_to_planner":
                    continue
                if tool_call.get("args", {}).get("locale") and tool_call.get("args", {}).get("research_topic"):
                    # 从工具调用中提取参数:  地域、研究主题
                    locale = tool_call.get("args", {}).get("locale")
                    research_topic = tool_call.get("args", {}).get("research_topic")
                    logger.info(f"协调器 从工具调用中提取参数: 地域={locale}, 研究主题={research_topic}")
                    break
        except Exception as e:
            logger.error(f'协调器 调用工具失败: {e}')
    else:
        logger.debug(f"协调器 未调用工具, 响应: {response}")
    messages = state.get("messages", [])
    if response.content:
        messages.append(HumanMessage(content=response.content, name="coordinator"))
    logger.info(f"协调器 结束. 跳转: {goto}")
    return Command(update={
        "messages": messages,
        "locale": locale,
        "research_topic": research_topic,
        # "resources": configurable.resources,
    }, goto=goto)
