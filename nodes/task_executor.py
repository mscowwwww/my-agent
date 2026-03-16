from typing import List, Dict, Any
from langgraph.types import Command, Send

from config.settings import TASK_MAX_RETRIES, TASK_MAX_THREADS
from core.state import AgentState, SubTask, TaskPlan
from core.enums import TaskTypeEnum, TaskPhaseEnum, RetryPolicyEnum
from core.constants import ADAPTER_MAP
from common.logger import get_logger

logger = get_logger()

# ===================== 主执行调度节点 =====================
def task_executor(state: AgentState) -> Command:
    """
    任务调度与执行节点
    1. 解析任务计划，筛选待执行的任务
    2. 处理任务依赖，生成并行执行任务
    3. 处理执行结果与异常重试
    """
    logger.info("===== 进入任务执行节点 =====")
    task_plan: TaskPlan = state.get("task_plan")
    task_results = state.get("task_results", {})
    step_count = state.get("step_count", 0)
    
    if not task_plan:
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
    
    # 1. 筛选可执行的任务（依赖已完成、状态为pending）
    pending_tasks: List[SubTask] = []
    for task in task_plan.task_list:
        if task.status != "pending":
            continue
        # 检查依赖是否全部完成
        depend_completed = all(
            dep_task_id in task_results
            for dep_task_id in task.depend_on
        )
        if depend_completed:
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
    
    # 3. 生成并行执行任务（LangGraph Send API）
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
        send_tasks = send_tasks[:TASK_MAX_THREADS]
    
    return Command(send=send_tasks)

def should_execute_task(state: AgentState) -> str:
    """
    条件判断函数：决定是否继续执行任务
    :param state: Agent状态
    :return: 下一个节点名称
    """
    # 【原有逻辑保留】你原有的任务判断逻辑（示例，可替换为你的实际逻辑）
    if hasattr(state, "pending_tasks") and len(state.pending_tasks) > 0:
        return "execute_single_task"  # 有未执行任务，走向单个任务执行节点
    else:
        return "fusion_node"  # 无未执行任务，走向融合节点

# ===================== 单任务执行函数 =====================
def execute_single_task(state: Dict[str, Any]) -> Dict[str, Any]:
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
        return {
            "task_id": task.task_id,
            "output_field": task.output_field,
            "result": task.model_dump(),
            "success": True
        }
    
    # 2. 检索类任务，调用对应适配器
    adapter_class = ADAPTER_MAP.get(task.task_type.value)
    if not adapter_class:
        error_msg = f"不支持的任务类型: {task.task_type}"
        logger.error(error_msg)
        task.status = "failed"
        task.error_msg = error_msg
        return {
            "task_id": task.task_id,
            "output_field": task.output_field,
            "result": task.model_dump(),
            "success": False,
            "error_msg": error_msg
        }
    
    # 3. 执行适配器
    adapter = adapter_class()
    success, result = adapter.execute(task, global_context)
    
    if success:
        task.status = "success"
        task.result = result
        logger.info(f"子任务执行成功: {task.task_id}")
        return {
            "task_id": task.task_id,
            "output_field": task.output_field,
            "result": result,
            "success": True
        }
    else:
        task.status = "failed"
        task.error_msg = result
        logger.error(f"子任务执行失败: {task.task_id} | 错误: {result}")
        return {
            "task_id": task.task_id,
            "output_field": task.output_field,
            "result": task.model_dump(),
            "success": False,
            "error_msg": result
        }

# ===================== 任务结果收集节点 =====================
def collect_task_result(state: AgentState, config, results: List[Dict[str, Any]]):
    """
    收集并行任务的执行结果，更新到全局状态
    """
    logger.info("===== 收集任务执行结果 =====")
    new_task_results = {}
    updated_task_list = []
    audit_logs = []
    
    # 获取原任务计划
    task_plan: TaskPlan = state.get("task_plan")
    task_map = {task.task_id: task for task in task_plan.task_list}
    
    # 处理每个任务的结果
    for result in results:
        task_id = result["task_id"]
        output_field = result["output_field"]
        success = result["success"]
        
        if success:
            new_task_results[output_field] = result["result"]
            # 更新任务状态
            if task_id in task_map:
                task_map[task_id].status = "success"
                task_map[task_id].result = result["result"]
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
                    task.error_msg = result.get("error_msg", "未知错误")
                    logger.warning(f"任务{task_id}执行失败，准备第{task.current_retry}次重试")
                else:
                    task.status = "failed"
                    task.error_msg = result.get("error_msg", "未知错误")
                    logger.error(f"任务{task_id}执行失败，已达最大重试次数")
            audit_logs.append({"task_id": task_id, "status": "failed", "error": result.get("error_msg")})
    
    # 更新任务计划
    updated_task_list = list(task_map.values())
    task_plan.task_list = updated_task_list
    
    return {
        "task_plan": task_plan,
        "task_results": new_task_results,
        "step_count": state.get("step_count", 0) + 1,
        "audit_logs": audit_logs,
    }