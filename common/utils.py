import json
from typing import List, Dict, Any
from langchain_core.documents import Document

# from config.settings import get_reranker, DEFAULT_TOP_K
from common.logger import get_logger

logger = get_logger()
# reranker = get_reranker()

# def rerank_documents(query: str, docs: List[Document], top_k: int = None) -> List[Document]:
#     """
#     对召回的文档进行重排序
#     :param query: 用户查询
#     :param docs: 召回的文档列表
#     :param top_k: 返回的top-k数量
#     :return: 重排序后的文档列表
#     """
#     if not docs:
#         return []
    
#     top_k = top_k or DEFAULT_TOP_K_RERANK
#     if len(docs) == 0:
#         return []
#     if len(docs) == 1:
#         return docs
    
#     # 构造重排输入
#     pairs = [[query, doc.page_content] for doc in docs]
#     try:
#         scores = reranker.compute_score(pairs, normalize=True)
#         # 按分数排序
#         scored_docs = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
#         # 取top-k，过滤低分结果
#         result = [doc for doc, score in scored_docs[:top_k] if score > 0.1]
#         logger.info(f"重排完成，召回{len(docs)}条，最终保留{len(result)}条")
#         return result
#     except Exception as e:
#         logger.error(f"重排失败: {str(e)}，返回原始前{top_k}条")
#         return docs[:top_k]

# def format_docs_with_source(docs: List[Document]) -> str:
#     """
#     格式化文档内容，强制绑定来源信息
#     :param docs: 文档列表
#     :return: 格式化后的文本
#     """
#     formatted = []
#     for idx, doc in enumerate(docs):
#         source = doc.metadata.get("source", "未知来源")
#         page = doc.metadata.get("page", "")
#         source_info = f"{source} - 第{page}页" if page else source
#         formatted.append(f"【来源：{source_info}】\n{doc.page_content.strip()}\n")
#     return "\n---\n".join(formatted)

def safe_json_parse(json_str: str) -> Dict[str, Any]:
    """
    安全的JSON解析，处理LLM输出的不规范JSON
    :param json_str: 待解析的JSON字符串
    :return: 解析后的字典
    """
    try:
        # 先尝试直接解析
        return json.loads(json_str)
    except json.JSONDecodeError:
        # 尝试提取```json包裹的内容
        if "```json" in json_str and "```" in json_str:
            start = json_str.find("```json") + 7
            end = json_str.rfind("```")
            json_content = json_str[start:end].strip()
            return json.loads(json_content)
        # 尝试提取{}包裹的内容
        elif "{" in json_str and "}" in json_str:
            start = json_str.find("{")
            end = json_str.rfind("}") + 1
            json_content = json_str[start:end].strip()
            return json.loads(json_content)
        else:
            raise ValueError(f"无法解析JSON内容: {json_str[:100]}...")