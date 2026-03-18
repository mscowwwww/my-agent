from typing import Dict, Any
from ddgs import DDGS
import json

from core.state import SubTask
from .base_adapter import BaseAdapter
from common.logger import get_logger
from langchain_community.document_loaders import WebBaseLoader

logger = get_logger()

class WebSearchAdapter(BaseAdapter):
    """外网搜索适配器"""
    
    def execute(self, task: SubTask, context: Dict[str, Any]) -> tuple[bool, str]:
        try:
            # 提取搜索query
            query = task.execution_requirement
            logger.info(f"开始外网搜索，query: {query}, task_id: {task.task_id}")
            
            # 执行搜索
            with DDGS() as ddgs:
                results = ddgs.text(
                    query=query,
                    region="cn-zh",
                    safesearch="moderate",
                    timelimit="y",
                    max_results=5
                )
            
            if not results:
                return False, "未搜索到相关结果"

            # 格式化结果，绑定来源
            formatted_list = []
            # for idx, r in enumerate(results):
            #     title = r.get("title", "")[:150]
            #     snippet = r.get("body", "")[:300]
            #     link = r.get("href", "")
            #     formatted_list.append(f"【来源：外网搜索 - {title}】\n内容摘要：{snippet}\n链接：{link}\n")
            for result in results:
                try:
                    url = result.get("href")
                    if not url:
                        continue
    
                    # 抓取网页完整内容
                    loader = WebBaseLoader(url)
                    docs = loader.load()
                    content = docs[0].page_content
                    formatted_list.append({
                        "url": url,
                        "content": content[:2000] # 防止 token 溢出，可截取或分块
                    })
                except:
                    None
            
            formatted_result = "\n---\n".join(formatted_list)
            logger.info(f"formatted_result: {formatted_result}")

            return True, formatted_result
        
        except Exception as e:
            error_msg = f"外网搜索失败: {str(e)}"
            logger.error(f"{error_msg}, task_id: {task.task_id}")
            return False, error_msg