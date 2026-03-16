# my_agent/core/constants.py
"""
全局常量定义（业界主流：集中管理映射关系）
"""
from core.enums import TaskTypeEnum
from adapters.web_search_adapter import WebSearchAdapter

# ====================== ADAPTER_MAP映射字典 ======================
ADAPTER_MAP = {
    # key：任务类型枚举值（与TaskTypeEnum对应）
    # value：对应的适配器类（注意：是类，不是实例）
    TaskTypeEnum.WEB_SEARCH.value: WebSearchAdapter,       # 检索类任务
    # 新增任务类型只需在此添加一行即可，无需修改任务执行逻辑
}