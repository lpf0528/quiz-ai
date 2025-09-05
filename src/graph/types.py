from langgraph.graph import MessagesState

from src.prompts.planner_model import Plan
from src.rag.retriever import Resource


class State(MessagesState):
    locale: str = "en-US"
    research_topic: str = ""
    observations: list[str] = []  # 观察
    resources: list[Resource] = []
    plan_iterations: int = 0
    current_plan: Plan | str = None
    final_report: str = ""
    auto_accepted_plan: bool = False
    enable_background_investigation: bool = True
    background_investigation_results: str = None

# def create_person(name: str, age: Optional[int] = 0) -> Person:
#     return Person(name=name, age=age)
