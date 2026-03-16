# langgraph_send_example.py
"""
LangGraph Send API 实际使用样例：并行文章生成系统

场景：给定一个主题列表，使用 Send 并行生成多篇文章摘要，
      最后汇总所有结果。
"""

from typing import Annotated, TypedDict
import operator
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

# ─────────────────────────────────────────
# 1. 定义状态
# ─────────────────────────────────────────

class OverallState(TypedDict):
    """主图的整体状态"""
    topics: list[str]                              # 输入的主题列表
    summaries: Annotated[list[str], operator.add]  # 汇总结果（自动合并）

class WorkerState(TypedDict):
    """每个并行 Worker 的私有状态"""
    topic: str
    summaries: list[str]  # Worker 写入后会 merge 进 OverallState


# ─────────────────────────────────────────
# 2. 定义节点
# ─────────────────────────────────────────

def generate_topics(state: OverallState) -> OverallState:
    """如果没有主题，生成默认主题列表（模拟输入阶段）"""
    if not state.get("topics"):
        return {"topics": ["人工智能", "量子计算", "气候变化"]}
    return state


def write_summary(state: WorkerState) -> dict:
    """
    Worker 节点：为单个主题生成摘要。
    每个 Send 调用都会独立运行这个节点。
    """
    topic = state["topic"]
    # 实际场景中可调用 LLM，这里用模拟数据
    summary = f"【{topic}】：这是关于'{topic}'的深度摘要。" \
              f"该领域正在快速发展，未来前景广阔。"
    print(f"  ✅ 完成摘要: {topic}")
    return {"summaries": [summary]}


def aggregate_results(state: OverallState) -> dict:
    """汇总节点：收集所有并行 Worker 的结果"""
    summaries = state.get("summaries", [])
    print(f"\n📦 汇总完成，共 {len(summaries)} 篇摘要")
    return {"summaries": summaries}


# ─────────────────────────────────────────
# 3. 核心：使用 Send 的边函数（fan-out）
# ─────────────────────────────────────────

def dispatch_to_workers(state: OverallState) -> list[Send]:
    """
    ⭐ Send 的关键用法：
    根据 topics 列表，为每个 topic 动态创建一个独立的 Send，
    每个 Send 都携带自己的初始状态，并行路由到 write_summary 节点。
    """
    send_tasks = []
    for topic in state["topics"]:
        send_tasks.append(Send("write_summary", {"aaa": topic, "summaries": []}))

    return send_tasks


# ─────────────────────────────────────────
# 4. 构建图
# ─────────────────────────────────────────

def build_graph():
    graph = StateGraph(OverallState)

    # 添加节点
    graph.add_node("generate_topics", generate_topics)
    graph.add_node("write_summary", write_summary)
    graph.add_node("aggregate_results", aggregate_results)

    # 添加边
    graph.add_edge(START, "generate_topics")

    # ⭐ 条件边 + Send：fan-out 并行分发
    graph.add_conditional_edges(
        "generate_topics",
        dispatch_to_workers,   # 返回 List[Send]，自动并行执行
        ["write_summary"]      # 声明可能的目标节点
    )

    # fan-in：所有 write_summary 完成后汇聚到 aggregate_results
    graph.add_edge("write_summary", "aggregate_results")
    graph.add_edge("aggregate_results", END)

    return graph.compile()


# ─────────────────────────────────────────
# 5. 运行
# ─────────────────────────────────────────

if __name__ == "__main__":
    app = build_graph()

    print("🚀 开始并行文章生成...\n")
    result = app.invoke({
        "topics": ["人工智能", "量子计算", "气候变化", "区块链"],
        "summaries": []
    })

    print("\n📄 最终结果：")
    for i, summary in enumerate(result["summaries"], 1):
        print(f"  {i}. {summary}")
