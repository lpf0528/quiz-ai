import logging
from typing import Annotated

from langchain_core.runnables import RunnableConfig

from langgraph.graph import StateGraph, START, END

from src.graph.nodes import coordinator_node, planner_node, human_feedback_node, research_team_node, \
    background_investigation_node, researcher_node
from src.graph.types import State
from src.prompts.planner_model import StepType

logger = logging.getLogger(__name__)


def continue_to_running_research_team(state: State):
    """继续运行研究团队节点"""
    current_plan = state.get('current_plan', '')
    if not current_plan or not current_plan.steps:
        logger.info("当前计划为空，需要移交给规划者。")
        return "planner"
    if all(step.execution_res for step in current_plan.steps):
        # 所有步骤都已执行，移交给规划者
        return "planner"
    incomplete_step = None  # 未完成step
    for step in current_plan.steps:
        if not step.execution_res:
            incomplete_step = step
            break

    if not incomplete_step:
        return "planner"
    # 研究步骤，移交给研究团队
    if incomplete_step.step_type == StepType.RESEARCH:
        return "research_team"
    # 编码步骤，移交给编码团队
    if incomplete_step.step_type == StepType.PROCESSING:
        return "coder"
    return "planner"


def _build_base_graph():
    """Build and return the base state graph with all nodes and edges."""
    builder = StateGraph(State)
    builder.add_edge(START, "coordinator")
    builder.add_node("coordinator", coordinator_node)
    builder.add_node("background_investigator", background_investigation_node)
    builder.add_node("planner", planner_node)
    builder.add_node("human_feedback", human_feedback_node)
    builder.add_node("research_team", research_team_node)
    builder.add_node("researcher", researcher_node)
    builder.add_edge("background_investigator", "planner")
    builder.add_conditional_edges(
        "research_team",
        continue_to_running_research_team,
        ["planner", "researcher", "coder"],
    )
    builder.add_edge("coordinator", END)
    return builder
