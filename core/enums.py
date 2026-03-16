from enum import Enum

class TaskTypeEnum(str, Enum):
    """子任务类型枚举"""
    USER_DOC_EXTRACT = "user_doc_extract"    # 用户文档提取
    BUILTIN_KB_RETRIEVE = "builtin_kb_retrieve"  # 固有知识库检索
    WEB_SEARCH = "web_search"                # 外网搜索
    COMPARE = "compare"                      # 对比分析
    SUMMARIZE = "summarize"                  # 总结
    GENERATE = "generate"                    # 内容生成
    POLISH = "polish"                        # 润色
    GENERAL_CHAT = "general_chat"            # 通用闲聊

class SourceTypeEnum(str, Enum):
    """信息来源枚举"""
    USER_TEMP_DOC = "user_temp_doc"          # 用户临时文档
    BUILTIN_KB = "builtin_kb"                # 固有知识库
    WEB_SEARCH = "web_search"                # 外网搜索
    PREVIOUS_TASK = "previous_task"          # 前置任务结果
    USER_INPUT = "user_input"                # 用户输入

class TaskPhaseEnum(str, Enum):
    """任务执行阶段枚举"""
    INITIAL = "initial"                      # 初始阶段
    PREPROCESS_DONE = "preprocess_done"      # 预处理完成
    PLANNING_DONE = "planning_done"          # 任务规划完成
    EXECUTING = "executing"                  # 执行中
    EXECUTION_DONE = "execution_done"        # 执行完成
    FUSION_DONE = "fusion_done"              # 融合处理完成
    FINISHED = "finished"                    # 完成
    ERROR = "error"                          # 异常

class RetryPolicyEnum(str, Enum):
    """任务失败重试策略枚举"""
    RETRY = "retry"                          # 重试
    SKIP = "skip"                            # 跳过
    ABORT = "abort"                          # 终止流程

class ReviewStatusEnum(Enum):
    PENDING = "pending"    # 待审核
    APPROVED = "approved"  # 审核通过
    REJECTED = "rejected"  # 审核驳回
    FAILED = "failed"      # 审核节点执行失败