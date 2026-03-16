import sys
from loguru import logger
from config.settings import LOG_DIR

# 移除默认handler
logger.remove()

# 控制台输出格式
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}:{line}</cyan> - <level>{message}</level>",
    level="INFO",
    enqueue=True
)

# 常规文件日志
logger.add(
    LOG_DIR / "agent_runtime.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}",
    level="DEBUG",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    enqueue=True,
    encoding="utf-8"
)

# 审计日志（单独文件，满足合规要求）
audit_logger = logger.bind(type="audit")
audit_logger.add(
    LOG_DIR / "audit.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | AUDIT | {message}",
    level="INFO",
    rotation="20 MB",
    retention="90 days",
    compression="zip",
    enqueue=True,
    encoding="utf-8"
)

def get_logger():
    """获取全局logger实例"""
    return logger

def get_audit_logger():
    """获取审计logger实例"""
    return audit_logger