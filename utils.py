import marvin
from typing import List
from datetime import datetime
import os
import asyncio
from schema import GeneratedContent, QualityMaintenance, WorkflowResult

# 简单的存储配置
DATA_DIR = "data"

async def aget_hot_topics() -> List[dict]:
    """异步获取多平台热点话题"""
    topics = []
    
    # 获取微博热搜
    topics.extend(await _aget_weibo_topics())
    
    # 获取小红书热门话题  
    topics.extend(await _aget_xiaohongshu_topics())
    
    # 获取百度热搜
    topics.extend(await _aget_baidu_topics())
    
    return topics

async def _aget_weibo_topics() -> List[dict]:
    """获取微博热搜话题"""
    # 实现微博API调用
    # 临时返回示例数据
    return [
        {"platform": "微博", "content": "开学季", "heat": "高"},
        {"platform": "微博", "content": "护眼健康", "heat": "中"},
        {"platform": "微博", "content": "职场穿搭", "heat": "中"},
        {"platform": "微博", "content": "数码产品", "heat": "高"}
    ]

async def _aget_xiaohongshu_topics() -> List[dict]:
    """获取小红书热门话题"""
    # 实现小红书话题获取
    # 临时返回示例数据
    return [
        {"platform": "小红书", "content": "学生党配镜", "heat": "高"},
        {"platform": "小红书", "content": "上班族护眼", "heat": "高"},
        {"platform": "小红书", "content": "时尚眼镜", "heat": "中"},
        {"platform": "小红书", "content": "近视防控", "heat": "高"}
    ]

async def _aget_baidu_topics() -> List[dict]:
    """获取百度热搜"""
    # 实现百度热搜API调用
    # 临时返回示例数据
    return [
        {"platform": "百度", "content": "视力保护", "heat": "中"},
        {"platform": "百度", "content": "眼镜品牌", "heat": "低"},
        {"platform": "百度", "content": "配镜攻略", "heat": "高"},
        {"platform": "百度", "content": "眼健康", "heat": "中"}
    ]

async def asave_result_to_file(result: WorkflowResult) -> str:
    """异步保存生成结果到txt文件 - 展示完整用户画像"""
    # 确保data目录存在
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # 生成时间戳文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{DATA_DIR}/result_{timestamp}.txt"
    
#     # 格式化输出内容 - 更详细的用户画像展示
#     output_content = f"""=== 小红书内容生成结果 ===
# 生成时间: {result.generation_timestamp}

# 【详细用户画像】
# 👤 人口统计：
# - 性别: {result.user_profile.gender}
# - 年龄: {result.user_profile.age}岁
# - 视力问题: {result.user_profile.profile_type}
# - 人群分类: {result.user_profile.age_group}
# - 教育背景: {result.user_profile.education_level}
# - 月收入: {result.user_profile.monthly_income}
# - 居住状况: {result.user_profile.living_situation}

# 💼 生活方式：
# - 工作强度: {result.user_profile.work_intensity}
# - 屏幕时长: {result.user_profile.screen_time}
# - 运动习惯: {result.user_profile.exercise_habit}
# - 睡眠质量: {result.user_profile.sleep_quality}

# 🛒 消费特征：
# - 决策风格: {result.user_profile.purchase_decision_style}
# - 价格敏感度: {result.user_profile.price_sensitivity}
# - 信息渠道: {', '.join(result.user_profile.information_source)}
# - 社交影响: {result.user_profile.social_influence}

# 😰 痛点与触发：
# - 具体痛点: {', '.join(result.user_profile.pain_points)}
# - 购买触发: {', '.join(result.user_profile.purchase_triggers)}

# 🎯 兴趣与偏好：
# - 兴趣话题: {', '.join(result.user_profile.interests)}
# - 内容偏好: {', '.join(result.user_profile.content_preference)}

# 🎭 个性特征：
# - 性格特点: {', '.join(result.user_profile.personality_traits)}
# - 担忧焦虑: {', '.join(result.user_profile.concerns_anxieties)}

# 【热点话题】
# {chr(10).join([f"- {topic.topic}" for topic in result.hot_topics])}

# 【生成内容】
# 标题: {result.generated_content.title}
# 正文: {result.generated_content.content}
# 标签: {', '.join(result.generated_content.label)}

# 【质量维护后内容】
# 标题: {result.quality_maintenance.title}
# 正文: {result.quality_maintenance.content}
# 标签: {', '.join(result.quality_maintenance.label)}

# 【针对性营销策略建议】
# 基于{result.user_profile.age}岁{result.user_profile.gender}性用户画像，建议：

# 1. 投放渠道优化：
#    - 根据性别年龄和教育背景选择最佳平台和时间段
#    - {result.user_profile.gender}性用户偏好的内容形式和互动方式

# 2. 内容策略调整：
#    - 结合年龄段特征调整语言风格和关注点
#    - 匹配{result.user_profile.gender}性用户的审美和功能需求

# 3. 价格策略制定：
#    - 基于收入水平({result.user_profile.monthly_income})和价格敏感度设计促销方案
#    - 考虑{result.user_profile.age}岁用户的消费能力和决策习惯

# 4. 服务流程优化：
#    - 针对{result.user_profile.gender}性用户的沟通偏好调整服务方式
#    - 关注该年龄段用户最关心的产品功能和使用场景
#    - 根据教育背景({result.user_profile.education_level})调整专业术语使用程度
# """
    output_content = f"""
{result.quality_maintenance.title}

{result.quality_maintenance.content}
{' '.join(result.generated_content.label)}
    """

    # 异步写入文件 - 使用内置的aiofiles替代方案
    try:
        import aiofiles
        async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
            await f.write(output_content)
    except ImportError:
        # 如果没有aiofiles，使用线程池执行同步写入
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _write_file_sync, filename, output_content)
    
    return filename

def _write_file_sync(filename: str, content: str) -> None:
    """同步写入文件的辅助函数"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)

def save_result_to_file(result: WorkflowResult) -> str:
    """同步保存生成结果到txt文件 - 向后兼容"""
    return asyncio.run(asave_result_to_file(result))
