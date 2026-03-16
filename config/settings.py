# my_agent/config/settings.py
"""
全局配置管理模块
- 原有配置：模型、日志、Agent流程相关
- 新增配置：文件存储、加密、合规、解析相关（大厂生产级）
"""
import os
from pathlib import Path

from dotenv import load_dotenv

#加载配置类
load_dotenv()

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 最大步长
MAX_STEPS = int(os.getenv("MAX_STEPS", 4))

# 默认语言
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "zh-CN")

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
AUDIT_LOG_ENABLE = os.getenv("AUDIT_LOG_ENABLE", "True")

# Task配置
TASK_PRIORITY = os.getenv("TASK_PRIORITY", "normal")
TASK_MAX_THREADS = int(os.getenv("TASK_MAX_THREADS", 4))
TASK_MAX_RETRIES = int(os.getenv("TASK_MAX_RETRIES", 3))
TASK_TIMEOUT = int(os.getenv("TASK_TIMEOUT", 300))

# 合规校验配置
FILE_TYPE_WHITELIST = ["txt", "pdf", "docx", "doc"]  # 文件格式白名单
MAX_FILE_SIZE = 100 * 1024 * 1024  # 单文件最大100MB
MAX_TEXT_LENGTH = 20000  # 用户输入文本最大长度
FILE_EXPIRE_DAYS = 7  # 文件过期天数（7天）
FILE_EXPIRE_SECONDS = FILE_EXPIRE_DAYS * 24 * 3600

# 向量库配置
# VECTOR_STORE_PATH = BASE_DIR / "data" / "knowledge_base"
# VECTOR_STORE_PATH.mkdir(exist_ok=True)
# EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")

# 解析配置
# DOC_CHUNK_SIZE = 800  # 文档分块大小（业界通用）
# DOC_CHUNK_OVERLAP = 100  # 分块重叠长度
# ASYNC_PARSE_THREADS = 4  # 异步解析线程数（避免资源耗尽）

# 文件存储配置
# USER_UPLOADED_FILES_PATH = BASE_DIR / "data" / "user_uploaded_files"  # 按user/thread隔离
# USER_UPLOADED_FILES_PATH.mkdir(exist_ok=True, parents=True)
# TEMP_USER_DOCS_PATH = BASE_DIR / "data" / "temp_user_docs"  # 解析后的向量库
# TEMP_USER_DOCS_PATH.mkdir(exist_ok=True)

# 元数据配置
# METADATA_DB_PATH = BASE_DIR / "data" / "metadata.db"

