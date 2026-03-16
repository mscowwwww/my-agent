# my_agent/common/compliance.py
"""
合规校验模块
- 原有逻辑：敏感词检测、输入合规校验
- 新增逻辑：文件合规校验（格式/大小/MD5）
"""
import re
import hashlib
from typing import Tuple, List
from config.settings import FILE_TYPE_WHITELIST, MAX_FILE_SIZE, MAX_TEXT_LENGTH
from core.enums import TaskTypeEnum
from common.logger import logger

# 敏感词库（示例）
SENSITIVE_WORDS = ["敏感词1", "敏感词2", "敏感词3"]

def check_sensitive_content(text: str) -> Tuple[bool, List[str]]:
    """
    敏感词检测
    :param text: 待检测文本
    :return: (是否合规, 命中的敏感词列表)
    """
    if not text:
        return False, []
    
    hit_words = []
    for word in SENSITIVE_WORDS:
        if word in text:
            hit_words.append(word)
    
    if hit_words:
        logger.warning(f"检测到敏感词：{hit_words}")
        return True, hit_words
    return False, []

def check_task_permission(user_id: str, task_type: str) -> Tuple[bool, str]:
    """
    任务权限校验（原有，完整保留）
    :param user_id: 用户ID
    :param task_type: 任务类型
    :return: (是否有权限, 提示信息)
    """
    # 示例逻辑（完整保留）
    admin_users = ["admin", "root"]
    if task_type == TaskTypeEnum.GENERATE.value and user_id not in admin_users:
        return False, "普通用户无生成类任务权限"
    return True, "权限校验通过"

def check_input_compliance(text: str) -> Tuple[bool, str]:
    """
    用户输入合规校验（长度、特殊字符）
    :param text: 用户输入
    :return: (是否合规, 提示信息)
    """
    # 长度校验
    if len(text) > MAX_TEXT_LENGTH:
        return False, f"输入文本过长（最大支持{MAX_TEXT_LENGTH}字符）"
    
    # 特殊字符校验（避免注入）
    dangerous_chars = re.findall(r'[;`$<>\\]', text)
    if dangerous_chars:
        return False, f"输入包含危险字符：{dangerous_chars}"
    
    return True, "输入合规"

def check_file_type(file_name: str) -> Tuple[bool, str]:
    """
    文件格式白名单校验
    :param file_name: 文件名
    :return: (是否合规, 结果信息/文件类型)
    """
    try:
        if not file_name or "." not in file_name:
            return False, "文件名格式错误（无后缀）"
        
        file_type = file_name.split(".")[-1].lower()
        if file_type not in FILE_TYPE_WHITELIST:
            return False, f"文件格式不支持（仅支持：{','.join(FILE_TYPE_WHITELIST)}）"
        
        return True, file_type
    except Exception as e:
        logger.error(f"文件类型校验失败：{str(e)}")
        return False, f"格式校验失败：{str(e)}"

def check_file_size(file_size: int) -> Tuple[bool, str]:
    """
    文件大小校验（防超大文件攻击）
    :param file_size: 文件字节数
    :return: (是否合规, 结果信息)
    """
    if file_size <= 0:
        return False, "文件为空"
    
    if file_size > MAX_FILE_SIZE:
        return False, f"文件过大（最大支持{MAX_FILE_SIZE/1024/1024:.1f}MB）"
    
    return True, f"文件大小合规（{file_size/1024:.1f}KB）"

def calculate_file_md5(file_path: str) -> Tuple[bool, str]:
    """
    计算文件MD5（防篡改、重复上传检测）
    :param file_path: 文件路径
    :return: (是否成功, MD5值/错误信息)
    """
    try:
        md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5.update(chunk)
        return True, md5.hexdigest()
    except Exception as e:
        logger.error(f"计算文件MD5失败：{str(e)}")
        return False, f"MD5计算失败：{str(e)}"