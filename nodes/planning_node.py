from langgraph.types import Command

from config.models import qwenFlash
from core.state import AgentState, TaskPlan, SubTask
from core.enums import TaskPhaseEnum, TaskTypeEnum, SourceTypeEnum, RetryPolicyEnum
from common.logger import get_logger, get_audit_logger
from common.utils import safe_json_parse

logger = get_logger()
audit_logger = get_audit_logger()
llm = qwenFlash

def planning_node(state: AgentState) -> Command:
    """
    意图理解与任务规划节点
    1. 理解用户核心诉求
    2. 拆解结构化子任务，定义依赖关系
    3. 校验任务计划合法性
    4. 输出标准化任务计划
    """
    logger.info("===== 进入任务规划节点 =====")
    thread_id = state.get("thread_id", "unknown")
    input_text = state.get("input_text", "")
    user_id = state.get("user_id", "unknown")
    user_role = state.get("user_role", "user")
    has_user_doc = bool(state.get("temp_vector_collection"))
    
    # 构造规划提示词
    system_prompt = f"""
    你是一个专业的任务规划专家，需要把用户的自然语言请求，拆解成结构化的可执行子任务。
    严格遵循以下规则：

    一、基础信息
    - 用户角色：{user_role}
    - 用户是否上传了文档：{'是，可使用user_doc_extract任务类型' if has_user_doc else '否，不能使用用户文档相关任务'}
    - 可用的任务类型与说明：
        1. user_doc_extract：从用户上传的文档中提取信息，target_source=user_temp_doc
        2. builtin_kb_retrieve：从企业固有知识库中检索信息，target_source=builtin_kb
        3. web_search：通过外网搜索获取实时信息，target_source=web_search
        4. compare：对比多个信息源的结果，做差异分析，target_source=previous_task
        5. summarize：对已有信息做总结，target_source=previous_task
        6. generate：基于已有信息生成内容，target_source=previous_task
        7. polish：润色优化文本，target_source=previous_task
        8. general_chat：通用闲聊/问答，无前置依赖

    二、任务拆解规则
    1. 先判断需要哪些信息源，先做信息获取类任务，再做处理类任务
    2. 处理类任务（compare/summarize等）必须依赖前置的信息获取任务，depend_on填写前置任务的task_id
    3. 每个子任务只做一件事，职责单一，不要把多个动作合并到一个任务
    4. task_id需保持唯一性，格式为 task_{user_id}_{thread_id}_序号_随机数
    5. 无依赖的任务可以并行执行，depend_on为空数组
    6. execution_requirement必须精准、具体，不能模糊
    7. 必须严格按照用户的诉求拆解，不要添加无关任务，也不要遗漏核心诉求

    三、输出要求
    必须严格输出JSON格式，不要任何其他内容、解释、markdown格式，JSON结构如下：
    {{
        "user_core_intent": "一句话提炼用户的核心诉求",
        "total_tasks": 子任务总数,
        "task_list": [
            {{
                "task_id": "task_user34234_yyyyMMdd_001_dhakfsdk",
                "task_type": "任务类型枚举值",
                "target_source": "信息来源枚举值",
                "execution_requirement": "精准的执行要求",
                "depend_on": ["依赖的task_id列表"],
                "retry_policy": "retry/skip/abort",
                "priority": 1
            }}
        ],
        "final_output_requirement": "最终输出的格式、内容要求，比如：按冲突点-建议的格式输出，每条结论标注来源"
    }}

    四、特殊规则
    - 如果用户的请求完全是闲聊，只需要生成一个general_chat类型的任务
    - 如果用户的请求无法处理，把is_valid设为false，填写invalid_reason
    """
    
    try:
        # 调用LLM生成任务计划
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"用户请求：{input_text}"}
        ])
        
        # 解析JSON
        plan_dict = safe_json_parse(response.content)
        task_plan = TaskPlan(**plan_dict)
        
        # 校验任务计划合法性
        if not task_plan.is_valid:
            logger.info(f"任务规划失败：请求不合法")
            error_msg = f"任务规划失败：{task_plan.invalid_reason}"
            logger.error(error_msg)
            return Command(
                update={
                    "task_plan": task_plan,
                    "error_message": error_msg,
                    "current_phase": TaskPhaseEnum.ERROR,
                    "final_output": error_msg,
                    "step_count": state["step_count"] + 1,
                },
                goto="output_node"
            )
        
        # 校验task_id唯一性
        task_id = [task.task_id for task in task_plan.task_list]
        if len(task_id) != len(set(task_id)): # set() 是 Python 的集合数据类型，它的特性是自动去重，只保留唯一的值。
            logger.info(f"任务规划失败：{task_id}存在重复")
            error_msg = "任务规划失败：task_id存在重复"
            logger.error(error_msg)
            return Command(
                update={
                    "error_message": error_msg,
                    "current_phase": TaskPhaseEnum.ERROR,
                    "final_output": error_msg,
                    "step_count": state["step_count"] + 1,
                },
                goto="output_node"
            )
        
        logger.info(f"任务规划完成：共拆解{task_plan.total_tasks}个子任务")
        audit_logger.info(f"任务规划完成 | thread_id: {thread_id} | 任务数: {task_plan.total_tasks}")
        
        # 更新状态
        return Command(
            update={
                "task_plan": task_plan,
                "current_phase": TaskPhaseEnum.PLANNING_DONE,
                "step_count": state["step_count"] + 1,
                "audit_logs": [{"step": "planning", "action": "plan_generated", "task_count": task_plan.total_tasks}]
            },
            goto="task_executor"
        )
    
    except Exception as e:
        error_msg = f"任务规划异常：{str(e)}"
        logger.error(f"{error_msg} | 原始输出: {response.content if 'response' in locals() else '无'}")
        return Command(
            update={
                "error_message": error_msg,
                "current_phase": TaskPhaseEnum.ERROR,
                "final_output": "抱歉，任务规划失败，请重新描述您的需求",
                "step_count": state["step_count"] + 1,
            },
            goto="output_node"
        )