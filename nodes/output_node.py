from langgraph.types import Command

from core.state import AgentState
from core.enums import TaskPhaseEnum
from common.logger import get_logger, get_audit_logger
from langgraph.graph import END

logger = get_logger()
audit_logger = get_audit_logger()

def output_node(state: AgentState) -> Command:
    """
    最终输出与审计落盘节点
    1. 整理最终输出
    2. 全链路审计日志落盘
    3. 状态收尾
    """
    logger.info("===== 进入最终输出节点 =====")
    thread_id = state.get("thread_id", "unknown")
    user_id = state.get("user_id", "unknown")
    final_output = state.get("final_output", "抱歉，未能生成有效结果")
    current_phase = state.get("current_phase")
    step_count = state.get("step_count", 0)
    
    # 审计日志落盘
    audit_logger.info(
        f"对话结束 | user_id: {user_id} | thread_id: {thread_id} | "
        f"最终阶段: {current_phase} | 总步数: {step_count}"
    )
    
    # 更新最终状态
    new_state = {
        "current_phase": TaskPhaseEnum.FINISHED if current_phase != TaskPhaseEnum.ERROR else TaskPhaseEnum.ERROR,
        "step_count": step_count + 1,
        "audit_logs": [{"step": "output", "action": "final_output_generated"}]
    }
    
    logger.info(f"对话流程结束，thread_id: {thread_id}")
    return Command(
        update=new_state,
        goto=END
    )