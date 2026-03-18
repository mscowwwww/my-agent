from typing import List, Dict, Any
from langgraph.types import Command, Send

from config.settings import TASK_MAX_RETRIES, TASK_MAX_THREADS
from core.state import AgentState, SubTask, TaskPlan
from core.enums import TaskTypeEnum, TaskPhaseEnum, RetryPolicyEnum
from core.constants import ADAPTER_MAP
from common.logger import get_logger

logger = get_logger()

# ===================== 主执行调度节点 =====================
def task_executor(state: AgentState):
    """
    任务调度与执行节点
    1. 解析任务计划，筛选待执行的任务
    2. 处理任务依赖，生成并行执行任务
    3. 处理执行结果与异常重试
    """
    logger.info("===== 进入任务执行节点 =====")
    task_plan: TaskPlan = state.get("task_plan")
    step_count = state.get("step_count", 0)

    if not task_plan:
        logger.info("未找到任务计划，无法执行")
        error_msg = "未找到任务计划，无法执行"
        logger.error(error_msg)
        return Command(
            update={
                "error_message": error_msg,
                "current_phase": TaskPhaseEnum.ERROR,
                "final_output": error_msg,
                "step_count": step_count + 1,
            },
            goto="output_node"
        )
    
    pending_tasks: List[SubTask] = []
    # 1. 筛选可执行的任务（依赖已完成、状态为pending）
    completed_tasks = {
        item.task_id 
        for item in task_plan.task_list 
        if item.status == "success"
    }
    for task in task_plan.task_list:
        if task.status != "pending":
            continue
        depend_completed = set(task.depend_on) - completed_tasks
        if not depend_completed:
            pending_tasks.append(task)
    
    # 2. 所有任务都处理完了，进入融合节点
    if not pending_tasks:
        all_completed = all(task.status == "success" for task in task_plan.task_list)
        if all_completed:
            logger.info("所有子任务执行完成，进入融合处理节点")
            return Command(
                update={
                    "current_phase": TaskPhaseEnum.EXECUTION_DONE,
                    "step_count": step_count + 1,
                },
                goto="fusion_node"
            )
        else:
            # 检查失败的任务
            failed_tasks = [t for t in task_plan.task_list if t.status == "failed"]
            error_msg = f"存在执行失败的任务: {[t.task_id for t in failed_tasks]}"
            logger.error(error_msg)
            return Command(
                update={
                    "error_message": error_msg,
                    "current_phase": TaskPhaseEnum.ERROR,
                    "final_output": "抱歉，任务执行过程中出现异常，请重试",
                    "step_count": step_count + 1,
                },
                goto="output_node"
            )
    
    logger.info(f"待执行任务数: {len(pending_tasks)}，开始并行执行")
    global_context = {
        "temp_vector_collection": state.get("temp_vector_collection"),
        "user_role": state.get("user_role"),
        "thread_id": state.get("thread_id"),
    }
    
    send_tasks = []
    for task in pending_tasks:
        # 标记为running
        task.status = "running"
        send_tasks.append(
            Send(
                "execute_single_task",
                {
                    "task": task,
                    "global_context": global_context
                }
            )
        )
    
    # 限制最大并行数
    if len(send_tasks) > TASK_MAX_THREADS:
        logger.info(f"限制最大并行数为:{TASK_MAX_THREADS}, 当前并行任务数为:{len(send_tasks)}")
        send_tasks = send_tasks[:TASK_MAX_THREADS]

    return Command(goto=send_tasks)

# ===================== 单任务执行函数 =====================
def execute_single_task(state: AgentState) -> Dict[str, Any]:
    """
    执行单个子任务（用于并行执行）
    :param state: 包含单个task和全局上下文的状态
    :return: 任务执行结果
    """
    task: SubTask = state["task"]
    global_context = state["global_context"]
    
    logger.info(f"执行子任务: {task.task_id} | 类型: {task.task_type}")
    
    # 1. 处理非检索类任务（直接返回，后续在fusion节点处理）
    if task.task_type in [TaskTypeEnum.COMPARE, TaskTypeEnum.SUMMARIZE, TaskTypeEnum.GENERATE, TaskTypeEnum.POLISH, TaskTypeEnum.GENERAL_CHAT]:
        task.status = "success"
        task.result = "待融合处理"
        logger.info(f"非检索类任务标记完成: {task.task_id}")
        return
    
    # 2. 检索类任务，调用对应适配器
    adapter_class = ADAPTER_MAP.get(task.task_type.value)
    if not adapter_class:
        error_msg = f"不支持的任务类型: {task.task_type}"
        logger.error(error_msg)
        task.status = "failed"
        task.result = task.model_dump()
        task.error_msg = error_msg
        return
    
    # 3. 执行适配器
    adapter = adapter_class()
    success, result = adapter.execute(task, global_context)
    
    if success:
        task.status = "success"
        task.result = result
        logger.info(f"子任务执行成功: {task.task_id}")
        return
    else:
        task.status = "failed"
        task.result = task.model_dump()
        task.error_msg = result
        logger.error(f"子任务执行失败: {task.task_id} | 错误: {result}")
        return

# ===================== 任务结果收集节点 =====================
def collect_task_result(state: AgentState):
    """
    收集并行任务的执行结果，更新到全局状态
    """
    logger.info("===== 收集任务执行结果 =====")
    updated_task_list = []
    audit_logs = []

    # 获取原任务计划
    task_plan: TaskPlan = state.get("task_plan")
    task_map = {task.task_id: task for task in task_plan.task_list}

    task_list = task_plan.task_list
    logger.info(f"任务收集结果: {task_list}")

    # 处理每个任务的结果
    for task in task_list:
        task_id = task.task_id
        task_result = task.result

        is_success = (task.status == "success")
        if is_success:
            # 更新任务状态
            if task_id in task_map:
                task_map[task_id].status = "success"
                task_map[task_id].result = task_result
            audit_logs.append({"task_id": task_id, "status": "success"})
            logger.info(f"任务结果收集完成: {task_id}")
        else:
            # 处理失败任务
            if task_id in task_map:
                task = task_map[task_id]
                task.current_retry += 1
                # 判断是否可以重试
                if task.current_retry < task.max_retries and task.retry_policy == RetryPolicyEnum.RETRY:
                    task.status = "pending"
                    task.error_msg = task.error_msg
                    logger.warning(f"任务{task_id}执行失败，准备第{task.current_retry}次重试")
                else:
                    task.status = "failed"
                    task.error_msg = task.error_msg
                    logger.error(f"任务{task_id}执行失败，已达最大重试次数")
            audit_logs.append({"task_id": task_id, "status": "failed", "error": task.error_msg})
    
    # 更新任务计划
    updated_task_list = list(task_map.values())
    task_plan.task_list = updated_task_list
    
    return {
        "task_plan": task_plan,
        "step_count": state.get("step_count", 0) + 1,
        "audit_logs": audit_logs,
    }