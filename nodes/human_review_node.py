# my_agent/nodes/human_review_node.py
"""
人工审核节点（生产级实现）
核心功能：
1. 提取待审核的核心信息（任务结果、文件信息、用户上下文）
2. 接收并校验人工审核结果
3. 标记审核状态，兼容LangGraph中断/恢复逻辑
4. 完整的异常处理和日志审计
"""
import uuid
from typing import Dict, Any, Optional
from dataclasses import asdict
from core.state import AgentState
from core.enums import ReviewStatusEnum  # 新增审核状态枚举（下方补充）
from common.logger import logger

def human_review_node(state: AgentState) -> Dict[str, Any]:
    """
    人工审核节点核心函数
    :param state: Agent结构化状态对象（包含所有上下文和任务信息）
    :return: 更新后的状态字典（包含审核结果和状态）
    """
    # 初始化返回状态（确保兼容原有结构）
    updated_state = asdict(state)
    updated_state["review_status"] = ReviewStatusEnum.PENDING.value
    updated_state["review_error_msg"] = ""
    
    try:
        logger.info(f"【人工审核节点】开始处理，用户ID：{state.user_id}，会话ID：{state.thread_id}")
        
        # ========== 步骤1：提取待审核核心信息（可根据业务扩展） ==========
        review_context = {
            "review_id": f"review_{uuid.uuid4()}",  # 生成唯一审核ID
            "user_id": state.user_id,
            "thread_id": state.thread_id,
            "timestamp": state.preprocess_time or "",  # 复用原有时间字段
            # 待审核的任务结果
            "completed_tasks": [
                {
                    "task_id": task.task_id,
                    "task_type": task.task_type.value if hasattr(task.task_type, "value") else str(task.task_type),
                    "task_status": task.status,
                    "task_result": task.result,
                    "error_msg": task.error_msg
                } for task in (state.completed_tasks or [])
            ],
            # 关联的文件信息
            "related_files": {
                "uploaded_file_ids": state.uploaded_file_ids or [],
                "vector_collections": state.user_doc_vector_collections or []
            },
            # 用户原始输入
            "user_input": state.user_input,
            # 预处理结果
            "preprocess_status": state.preprocess_status
        }
        
        # 记录待审核信息（生产环境可推送至审核平台/数据库）
        logger.info(f"【人工审核节点】待审核信息：{review_context}")
        updated_state["review_context"] = review_context  # 存储待审核上下文
        
        # ========== 步骤2：接收并校验人工审核结果 ==========
        human_review_result: Optional[Dict[str, Any]] = state.human_review_result
        if human_review_result:
            # 校验审核结果的必填字段
            required_review_fields = ["approved", "review_comment"]
            missing_fields = [f for f in required_review_fields if f not in human_review_result]
            if missing_fields:
                raise ValueError(f"人工审核结果缺少必填字段：{','.join(missing_fields)}")
            
            # 标记审核状态
            if human_review_result.get("approved"):
                updated_state["review_status"] = ReviewStatusEnum.APPROVED.value
                logger.info(f"【人工审核节点】用户{state.user_id}审核通过，备注：{human_review_result['review_comment']}")
            else:
                updated_state["review_status"] = ReviewStatusEnum.REJECTED.value
                logger.warning(f"【人工审核节点】用户{state.user_id}审核驳回，备注：{human_review_result['review_comment']}")
            
            # 存储审核结果（包含审核人、时间等扩展字段）
            updated_state["human_review_result"] = {
                **human_review_result,
                "review_id": review_context["review_id"],
                "review_time": state.preprocess_time or ""  # 可替换为当前时间
            }
            updated_state["is_human_review_completed"] = True
        else:
            # 未收到审核结果，标记为待审核（触发LangGraph中断）
            logger.warning(f"【人工审核节点】用户{state.user_id}未提交审核结果，等待人工输入...")
            updated_state["review_status"] = ReviewStatusEnum.PENDING.value
            updated_state["is_human_review_completed"] = False
        
        # ========== 步骤3：返回更新后的状态 ==========
        logger.info(f"【人工审核节点】处理完成，审核状态：{updated_state['review_status']}")
        return updated_state

    except Exception as e:
        error_msg = f"人工审核失败: {str(e)}"
        updated_state["review_status"] = ReviewStatusEnum.FAILED.value
        updated_state["review_error_msg"] = error_msg
        updated_state["is_human_review_completed"] = False
        logger.error(error_msg)
        return updated_state