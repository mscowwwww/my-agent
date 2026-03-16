from typing import Optional, Annotated, TypedDict, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
import operator

from .enums import TaskTypeEnum, SourceTypeEnum, TaskPhaseEnum, RetryPolicyEnum

# ===================== 自定义Reducer =====================
def merge_dicts(old: dict, new: dict) -> dict:
    """字典合并Reducer，不覆盖原有键值对"""
    return {**old, **new}

def merge_task_results(old: dict, new: dict) -> dict:
    """任务结果合并Reducer，按task_id更新"""
    return {**old, **new}

# ===================== 子任务Schema =====================
class SubTask(BaseModel):
    """子任务结构化定义"""
    task_id: str = Field(description="子任务唯一ID，格式：task_xxx")
    task_type: TaskTypeEnum = Field(description="子任务类型")
    target_source: SourceTypeEnum = Field(description="目标信息来源")
    execution_requirement: str = Field(description="执行要求，精准描述要做的事")
    depend_on: List[str] = Field(default_factory=list, description="依赖的前置任务ID列表")
    output_field: str = Field(description="结果存储的字段名，全局唯一")
    retry_policy: RetryPolicyEnum = Field(default=RetryPolicyEnum.RETRY, description="失败重试策略")
    priority: int = Field(default=1, description="执行优先级，数字越小优先级越高")
    max_retries: int = Field(default=2, description="最大重试次数")
    current_retry: int = Field(default=0, description="当前重试次数")
    status: Literal["pending", "running", "success", "failed"] = Field(default="pending", description="任务状态")
    result: str = Field(default="", description="任务执行结果")
    error_msg: str = Field(default="", description="错误信息")

# ===================== 任务计划Schema =====================
class TaskPlan(BaseModel):
    """全局任务计划定义"""
    user_core_intent: str = Field(description="提炼的用户核心诉求")
    total_tasks: int = Field(description="子任务总数")
    task_list: List[SubTask] = Field(description="子任务列表")
    final_output_requirement: str = Field(description="最终输出的格式与内容要求")
    is_valid: bool = Field(default=True, description="任务计划是否合法")
    invalid_reason: str = Field(default="", description="不合法的原因")

# ===================== Agent全局状态定义 =====================
class AgentState(TypedDict):
    """Agent全生命周期状态"""
    # 基础输入输出
    input_text: str
    messages: Annotated[List[BaseMessage], operator.add]
    final_output: str

    # 用户与会话信息
    user_id: str
    thread_id: str
    user_role: Literal["admin", "user", "guest"] = "user"

    # 任务与流程管控
    task_plan: TaskPlan
    current_phase: TaskPhaseEnum
    step_count: int
    error_message: str

    # 多源任务执行结果（按output_field存储，key=output_field, value=结果）
    task_results: Annotated[Dict[str, Any], merge_task_results]

    # 用户文档相关
    user_documents: List[Dict[str, Any]]  # 用户上传的文档列表 [{content, source, doc_id}]
    temp_vector_collection: str  # 当前会话的临时向量库集合名

    # 元数据与审计
    metadata: Annotated[dict, merge_dicts]
    human_approved: bool
    audit_logs: Annotated[List[Dict[str, Any]], operator.add]

    # 【新增】人工审核相关字段
    human_review_result: Optional[Dict[str, Any]] = None  # 人工审核结果（approved/comment）
    is_human_review_completed: bool = False               # 审核是否完成
    review_status: Optional[str] = None                   # 审核状态（pending/approved/rejected/failed）
    review_context: Optional[Dict[str, Any]] = None       # 待审核上下文
    review_error_msg: Optional[str] = ""                  # 审核节点异常信息