from abc import ABC, abstractmethod
from typing import Dict, Any
from core.state import SubTask

class BaseAdapter(ABC):
    """适配器基类，定义统一的执行接口"""
    
    @abstractmethod
    def execute(self, task: SubTask, context: Dict[str, Any]) -> tuple[bool, str]:
        """
        执行子任务
        :param task: 子任务对象
        :param context: 全局上下文（AgentState）
        :return: (是否执行成功, 执行结果/错误信息)
        """
        pass

