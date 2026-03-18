from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from core.state import AgentState
from nodes.output_node import output_node
from nodes.fusion_node import fusion_node
from nodes.planning_node import planning_node
from nodes.preprocess_node import preprocess_node
from nodes.human_review_node import human_review_node
from nodes.task_executor import (
    task_executor,
    execute_single_task,
    collect_task_result,
)
from common.logger import get_logger

logger = get_logger()

def build_agent_graph():
    """构建Agent主流程图"""
    logger.info("开始构建Agent状态图...")
    
    # 初始化状态图
    builder = StateGraph(AgentState)
    
    # 添加节点
    builder.add_node("preprocess_node", preprocess_node)
    builder.add_node("planning_node", planning_node)
    builder.add_node("task_executor", task_executor)
    builder.add_node("execute_single_task", execute_single_task)
    builder.add_node("collect_task_result", collect_task_result)
    builder.add_node("human_review_node", human_review_node)
    builder.add_node("fusion_node", fusion_node)
    builder.add_node("output_node", output_node)

    # 构建主流程边
    builder.add_edge(START, "preprocess_node")
    builder.add_edge("preprocess_node", "planning_node")
    builder.add_edge("planning_node", "task_executor")
    # 并行任务收集逻辑
    # builder.add_conditional_edges(
    #     "task_executor",
    #     should_execute_task,
    #     {
    #         "execute_single_task": "execute_single_task",
    #         "fusion_node": "fusion_node"
    #     }
    # )
    builder.add_edge("execute_single_task", "task_executor")
    builder.add_edge("collect_task_result", "task_executor")
    
    # 执行完成后进入融合节点
    builder.add_edge("fusion_node", "output_node")
    builder.add_edge("output_node", END)
    
    # 编译图
    memory = MemorySaver()
    app = builder.compile(
        checkpointer=memory,
        interrupt_before=["human_review_node"]  # 预留人工审核中断点
    )
    
    logger.info("Agent状态图构建完成")
    return app

# 全局Agent实例
agent_app = build_agent_graph()