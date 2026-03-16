import uuid
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from graph.agent_graph import agent_app
from common.logger import get_logger

logger = get_logger()

def init_system():
    """系统初始化"""
    logger.info("===== 系统初始化开始 =====")
    # 初始化固有知识库
    # init_builtin_knowledge_base(force_rebuild=False)
    logger.info("===== 系统初始化完成 =====")

def run_demo():
    """运行演示示例"""
    # 初始化系统
    init_system()
    
    # 会话配置
    thread_id = str(uuid.uuid4())
    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": "test_user_001",
        }
    }
    logger.info(f"演示会话ID: {thread_id}")
    
    # 示例1：用户上传文档 + 对比固有知识库
    # print("\n" + "="*80)
    # print("示例1：用户上传合同文档，对比公司制度")
    # print("="*80)
    
    # user_input = """
    # 这是我上传的项目合同文档：
    # 合同名称：XX项目服务合同
    # 付款条款：合同签订后15个工作日内，甲方向乙方支付合同总金额的30%作为预付款；项目验收合格后10个工作日内，支付65%的尾款；剩余5%作为质保金，质保期满后无问题一次性支付。
    # 保密条款：双方应对合同内容保密，保密期限为合同履行完毕后2年。
    # 违约责任：任何一方违约，需向对方支付合同总金额10%的违约金。

    # 请帮我完成以下操作：
    # 1. 提取这份合同里的付款、保密、违约责任条款
    # 2. 查一下公司的《财务管理制度》和《保密管理制度》里的相关规定
    # 3. 对比合同条款和公司制度有没有冲突，给我合规建议，每条结论要标注来源
    # """
    
    # # 执行Agent
    # result = agent_app.invoke(
    #     {
    #         "input_text": user_input,
    #         "thread_id": thread_id,
    #         "user_id": "test_user_001",
    #         "user_role": "user",
    #     },
    #     config
    # )
    
    # # 输出结果
    # print("\n📝 最终输出结果：")
    # print(result["final_output"])
    # print("\n" + "="*80)
    
    # 示例2：实时搜索场景
    print("\n" + "="*80)
    print("示例2：实时天气查询与建议生成")
    print("="*80)
    
    thread_id_2 = str(uuid.uuid4())
    config_2 = {
        "configurable": {
            "thread_id": thread_id_2,
            "user_id": "test_user_001",
        }
    }
    
    user_input_2 = "查一下深圳今天的天气，然后帮我写一份周末出行的建议"
    result_2 = agent_app.invoke(
        {
            "input_text": user_input_2,
            "thread_id": thread_id_2,
            "user_id": "test_user_001",
            "user_role": "user",
        },
        config_2
    )
    
    print("\n📝 最终输出结果：")
    print(result_2["final_output"])
    print("\n" + "="*80)

if __name__ == "__main__":
    run_demo()