import logging
import uuid

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Interrupt, Command

from src.graph.builder import _build_base_graph

# 构建图
graph_builder = _build_base_graph()
# 编译图
memory = InMemorySaver()
graph = graph_builder.compile(checkpointer=memory)
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

config = {"configurable": {"thread_id": uuid.uuid4()}}


def stream_graph_updates(user_input: dict | Command):
    for event in graph.stream(user_input, config=config):

        if '__interrupt__' in event:
            a = input('请输入')
            stream_graph_updates(Command(resume=a))
        else:
            for value in event.values():
                try:
                    print("Assistant:", value)
                except Exception as e:
                    print(value)
                    logger.error(f"Assistant 回复错误: {e}")
                    raise e


while True:
    try:
        print('------------------------------------')
        user_input = "什么是langchain"  # input("User: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break
        stream_graph_updates({"messages": [{"role": "user", "content": user_input}],
                              "auto_accepted_plan": True, 'enable_background_investigation': True})
        break
    except:
        break
