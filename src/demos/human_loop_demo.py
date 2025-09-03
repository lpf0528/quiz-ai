from typing import TypedDict
import uuid
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.constants import START
from langgraph.graph import StateGraph

from langgraph.types import interrupt, Command


class State(TypedDict):
    some_text: str


def human_node(state: State):
    print('human_node')
    value = interrupt('human_node')
    # value = 'human_node'
    print('human_node', value)
    return {
        "some_text": value
    }


def human_node2(state: State):
    print('human_node2')
    value = interrupt('human_node2')
    # value = 'human_node2'

    print('human_node2', value)
    return {
        "some_text": value
    }


# Build the graph
graph_builder = StateGraph(State)
graph_builder.add_node("human_node", human_node)
graph_builder.add_node("human_node2", human_node2)
graph_builder.add_edge(START, "human_node")
graph_builder.add_edge("human_node", "human_node2")
checkpointer = InMemorySaver()
graph = graph_builder.compile(checkpointer=checkpointer)
# Pass a thread ID to the graph to run it.
config = {"configurable": {"thread_id": uuid.uuid4()}}


def xxx(data):
    for event in graph.stream(data, config=config):
        if '__interrupt__' in event:
            a = input('请输入')
            xxx(Command(resume=a))
        else:
            print('--------->', event)


xxx({"some_text": "original text"})
