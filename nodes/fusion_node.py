from langgraph.types import Command

from config.models import qwenFlash
from core.state import AgentState
from core.enums import TaskPhaseEnum, TaskTypeEnum
from common.logger import get_logger

logger = get_logger()
llm = qwenFlash

def fusion_node(state: AgentState) -> Command:
    """
    信息融合与二次处理节点
    1. 基于任务计划，处理对比、总结、生成等二次处理任务
    2. 强制绑定信息来源，防控幻觉
    3. 按照最终输出要求生成结果
    """
    logger.info("===== 进入信息融合节点 =====")
    task_plan = state.get("task_plan")
    task_results = state.get("task_results", {})
    input_text = state.get("input_text", "")
    
    if not task_plan:
        error_msg = "未找到任务计划"
        return Command(
            update={"error_message": error_msg, "final_output": error_msg, "current_phase": TaskPhaseEnum.ERROR},
            goto="output_node"
        )
    
    # 1. 提取处理类任务
    process_tasks = [
        task for task in task_plan.task_list
        if task.task_type in [TaskTypeEnum.COMPARE, TaskTypeEnum.SUMMARIZE, TaskTypeEnum.GENERATE, TaskTypeEnum.POLISH, TaskTypeEnum.GENERAL_CHAT]
    ]
    
    # 2. 构造融合上下文
    context_parts = []
    context_parts.append(f"用户原始请求：{input_text}")
    context_parts.append("\n【已获取的信息结果】")
    for field_name, result_content in task_results.items():
        context_parts.append(f"--- {field_name} ---\n{result_content}\n")
    
    context = "\n".join(context_parts)
    
    # 3. 构造处理指令
    system_prompt = f"""
    你是一个专业的信息处理专家，需要基于已获取的信息，完成用户要求的处理任务。
    严格遵循以下规则：
    1. 只能使用【已获取的信息结果】中的内容，绝对不能编造、虚构任何信息
    2. 所有结论必须标注对应的信息来源，比如【来源：用户上传文档】、【来源：固有知识库】
    3. 如果信息不足，如实说明，不要瞎编
    4. 严格按照用户的最终输出要求生成内容，格式清晰，逻辑通顺
    5. 如果是闲聊，直接友好回复即可

    最终输出要求：{task_plan.final_output_requirement}
    """
    
    try:
        # 调用LLM做融合处理
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ])
        
        final_output = response.content
        logger.info("信息融合处理完成")
        
        return Command(
            update={
                "final_output": final_output,
                "current_phase": TaskPhaseEnum.FUSION_DONE,
                "step_count": state.get("step_count", 0) + 1,
                "messages": state.get("messages", []) + [response],
            },
            goto="output_node"
        )
    
    except Exception as e:
        error_msg = f"信息融合处理失败: {str(e)}"
        logger.error(error_msg)
        return Command(
            update={
                "error_message": error_msg,
                "current_phase": TaskPhaseEnum.ERROR,
                "final_output": "抱歉，信息处理失败，请重试",
                "step_count": state.get("step_count", 0) + 1,
            },
            goto="output_node"
        )