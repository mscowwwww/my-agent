import os
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings

from langchain_community.embeddings import DashScopeEmbeddings

#加载配置类
load_dotenv()

# 模型名称 (模型ID)
# 例如: "qwen-plus", "deepseek-chat", "glm-4", "moonshot-v1-8k"

# Base URL (接口地址 )
# 阿里云百炼: https://dashscope.aliyuncs.com/compatible-mode/v1
# DeepSeek:   https://api.deepseek.com/v1
# 智谱 AI:     https://open.bigmodel.cn/api/paas/v4
# Moonshot:   https://api.moonshot.cn/v1
# 本地 Ollama: http://localhost:11434/v1
# glm(免费): https://open.bigmodel.cn/api/paas/v4

qwenCoderPlus = ChatOpenAI(
    model="qwen3-coder-plus",
    api_key=os.getenv("ALI_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    temperature= 0.7,               # 创造性控制：低值用于逻辑/工具调用，高值用于创意写作
    max_completion_tokens=10000,    # 输出长度限制：防止无限生成或成本失控
    timeout= 60,                    # 网络超时：长任务需增加此值
    max_retries=2,                  # 自动重试：应对网络波动或 API 限流
    streaming=False,                # 流式输出：Agent 内部推理通常关闭，最终回答可开启
    verbose=True                   # 内部日志：生产环境建议关闭
)


qwenFlash = ChatOpenAI(
    model="qwen3.5-flash",
    api_key=os.getenv("ALI_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    temperature= 0.7,               # 创造性控制：低值用于逻辑/工具调用，高值用于创意写作
    max_completion_tokens=10000,    # 输出长度限制：防止无限生成或成本失控
    timeout= 60,                    # 网络超时：长任务需增加此值
    max_retries=2,                  # 自动重试：应对网络波动或 API 限流
    streaming=False,                # 流式输出：Agent 内部推理通常关闭，最终回答可开启
    verbose=True                   # 内部日志：生产环境建议关闭
)

qwenEmbedding = DashScopeEmbeddings(
    model="text-embedding-v1",
    dashscope_api_key=os.getenv("ALI_API_KEY")
)

glmFlash = ChatOpenAI(
    model="glm-4.7-flash",
    api_key=os.getenv("GLM_API_KEY"),
    base_url="https://open.bigmodel.cn/api/paas/v4",
    temperature= 0.7,
    timeout= 30,
)