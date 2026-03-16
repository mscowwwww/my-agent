from langgraph.types import Command
from langchain_core.messages import HumanMessage

from config.settings import MAX_STEPS
from core.state import AgentState
from core.enums import TaskPhaseEnum
from common.compliance import check_sensitive_content
from common.logger import get_logger, get_audit_logger

logger = get_logger()
audit_logger = get_audit_logger()

def preprocess_node(state: AgentState) -> Command:
    """
    前置预处理与准入管控节点
    1. 初始化状态
    2. 合规校验（敏感词检测）
    3. 用户文档提取与处理
    4. 基础参数校验
    """
    logger.info("===== 进入前置预处理节点 =====")
    thread_id = state.get("thread_id", "unknown")
    user_id = state.get("user_id", "unknown")
    input_text = state.get("input_text", "")
    
    # 审计日志
    audit_logger.info(f"用户请求预处理 | user_id: {user_id} | thread_id: {thread_id} | 输入长度: {len(input_text)}")
    
    # 1. 初始化状态
    new_state = {
        "step_count": state.get("step_count", 0) + 1,
        "current_phase": TaskPhaseEnum.INITIAL,
        "audit_logs": [{"step": "preprocess", "time": str(logger._core.time), "action": "start_preprocess"}],
        "error_message": "",
    }
    
    # 2. 敏感内容校验
    has_sensitive, sensitive_word = check_sensitive_content(input_text)
    if has_sensitive:
        error_msg = f"输入内容包含敏感信息：{sensitive_word}，无法处理"
        logger.warning(error_msg)
        audit_logger.warning(f"敏感内容拦截 | user_id: {user_id} | thread_id: {thread_id} | 敏感词: {sensitive_word}")
        return Command(
            update={
                **new_state,
                "error_message": error_msg,
                "current_phase": TaskPhaseEnum.ERROR,
                "final_output": error_msg,
            },
            goto="output_node"
        )
    
    # 3. 初始化消息列表
    if not state.get("messages"):
        new_state["messages"] = [HumanMessage(content=input_text)]
    
    # 4. 检测并处理用户上传的文档内容
    # 识别用户输入中是否包含大段文档内容（简单判断：文本长度>500，且包含"文档""内容""帮我看一下这段"等关键词）
    
    
    # 5. 步数超限校验
    if new_state["step_count"] >= MAX_STEPS:
        error_msg = "对话轮次已达上限，请重新发起对话"
        logger.warning(error_msg)
        return Command(
            update={
                **new_state,
                "error_message": error_msg,
                "current_phase": TaskPhaseEnum.ERROR,
                "final_output": error_msg,
            },
            goto="output_node"
        )
    
    # 预处理完成，进入任务规划节点
    new_state["current_phase"] = TaskPhaseEnum.PREPROCESS_DONE
    logger.info("前置预处理完成，进入任务规划节点")
    return Command(
        update=new_state,
        goto="planning_node"
    )