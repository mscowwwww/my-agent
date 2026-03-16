# my_agent/common/document_parser.py
"""
文档解析模块
- 原有逻辑：文档解析、分块、向量化
- 重构逻辑：按需异步解析（非阻塞，大厂生产级）
"""
import threading
from typing import Tuple, Optional, Callable
from io import BytesIO
from config.settings import (
    DOC_CHUNK_SIZE,
    DOC_CHUNK_OVERLAP,
    ASYNC_PARSE_THREADS,
    TEMP_USER_DOCS_PATH
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from common.logger import logger

# ====================== 原有初始化逻辑（保留，新增异步配置） ======================
# 文本分块器（业界通用配置）
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=DOC_CHUNK_SIZE,
    chunk_overlap=DOC_CHUNK_OVERLAP,
    separators=["\n\n", "\n", "。", "！", "？", "，", "、"]
)

# Embedding初始化
embeddings = OpenAIEmbeddings()

# 异步解析线程池
parse_thread_pool = threading.Semaphore(ASYNC_PARSE_THREADS)

def parse_file_content(
    file_content: bytes,
    file_type: str,
    file_id: str
) -> Tuple[bool, str, Optional[str]]:
    """
    同步解析文件内容（核心：按需解析，非主动触发）
    :param file_content: 解密后的文件内容
    :param file_type: 文件类型（txt/pdf/docx）
    :param file_id: 文件ID（关联向量库）
    :return: (是否成功, 提示信息, 向量库名称)
    """
    try:
        # 1. 加载文件（适配不同格式）
        if file_type == "pdf":
            loader = PyPDFLoader(BytesIO(file_content))
        elif file_type == "txt":
            loader = TextLoader(BytesIO(file_content), encoding="utf-8")
        elif file_type == "docx":
            loader = Docx2txtLoader(BytesIO(file_content))
        else:
            return False, f"暂不支持解析{file_type}格式文件", None
        
        documents = loader.load()
        if not documents:
            return False, "文件内容为空", None

        # 2. 文本分块（原有逻辑保留）
        split_docs = text_splitter.split_documents(documents)
        logger.info(f"文件{file_id}分块完成，共{len(split_docs)}块")

        # 3. 向量化存储（按file_id命名，便于关联）
        vector_collection = f"user_doc_{file_id}"
        vector_store_path = TEMP_USER_DOCS_PATH / vector_collection
        Chroma.from_documents(
            split_docs,
            embeddings,
            persist_directory=str(vector_store_path)
        )

        return True, f"文件解析完成，向量库：{vector_collection}", vector_collection

    except Exception as e:
        logger.error(f"文件{file_id}解析失败：{str(e)}")
        return False, f"解析失败：{str(e)}", None

def trigger_parse_async(
    file_id: str,
    file_content: bytes,
    file_type: str,
    callback: Optional[Callable[[str, bool, str, Optional[str]], None]] = None
) -> bool:
    """
    异步触发文件解析（非阻塞，大厂生产级）
    :param file_id: 文件ID
    :param file_content: 解密后的文件内容
    :param file_type: 文件类型
    :param callback: 解析完成后的回调函数（file_id, success, msg, vector_collection）
    :return: 是否触发成功
    """
    def _parse_task():
        """异步解析子任务"""
        with parse_thread_pool:  # 线程池限流
            success, msg, vector_collection = parse_file_content(file_content, file_type, file_id)
            if callback:
                callback(file_id, success, msg, vector_collection)

    try:
        # 启动异步线程（守护线程，避免阻塞主流程）
        threading.Thread(target=_parse_task, daemon=True).start()
        logger.info(f"文件{file_id}异步解析已触发")
        return True
    except Exception as e:
        logger.error(f"触发文件{file_id}异步解析失败：{str(e)}")
        return False