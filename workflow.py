import marvin
from typing import List
from datetime import datetime
import asyncio
import json
import os

# 将相对导入改为绝对导入
from schema import (
    UserProfile, HotTopic, ContentStrategy, 
    GeneratedContent, QualityMaintenance, WorkflowResult
)
from utils import aget_hot_topics, asave_result_to_file
from prompts import USER_PROFILE_GENERATOR, HOT_TOPIC_EXTRACTOR, CONTENT_STRATEGIST, CONTENT_GENERATOR, QUALITY_MAINTAINER
from randomizer import user_randomizer

async def agenerate_user_profile() -> UserProfile:
    """异步生成增强版用户画像 - 基于随机配置约束"""
    
    # 生成随机配置
    config = user_randomizer.generate_random_config()
    
    # 获取性格特征详情
    personality_traits = user_randomizer.get_personality_traits(config.user_personality)
    
    # 格式化性格特征描述
    personality_details = f"""
**决策风格**: {', '.join(personality_traits['decision_style'])}
**价格敏感度**: {', '.join(personality_traits['price_sensitivity'])}
**信息渠道偏好**: {', '.join(personality_traits['information_sources'])}
**内容偏好**: {', '.join(personality_traits['content_preferences'])}
**主要担忧**: {', '.join(personality_traits['concerns'])}
    """
    
    # 应用随机配置到提示词
    enhanced_prompt = USER_PROFILE_GENERATOR.format(
        gender=config.gender,
        age_range=config.age_range,
        vision_type=config.vision_type,
        user_personality=config.user_personality,
        education_level=config.education_level,
        work_nature=config.work_nature,
        life_pace=config.life_pace,
        income_level=config.income_level,
        living_situation=config.living_situation,
        city_tier=config.city_tier,
        personality_details=personality_details
    )
    
    agent = marvin.Agent(
        model=marvin.defaults.model,
        model_settings={"temperature": 1.2, "top_p": 0.9}
    )
    
    # 修改：明确指定生成单个实例，并添加错误处理
    result = await marvin.generate_async(
        target=UserProfile,
        agent=agent,
        instructions=enhanced_prompt,
        n=1  # 明确指定生成1个实例
    )
    
    # 如果返回的是列表，取第一个元素
    if isinstance(result, list):
        if len(result) > 0:
            return result[0]
        else:
            raise ValueError("生成的用户画像为空列表")
    
    return result

async def aextract_hot_topics() -> List[HotTopic]:
    """异步获取并筛选热点话题"""
    raw_topics = await aget_hot_topics()
    
    # 修复：正确处理原始话题数据，raw_topics是字典列表
    topics_prompt = HOT_TOPIC_EXTRACTOR.format(
        topics="\n".join([f"{topic['content']}" for topic in raw_topics])
    )
    
    # 简化：直接返回相关话题列表，不再过滤评分
    all_topics = await marvin.generate_async(
        target=HotTopic,
        instructions=topics_prompt,
        n=5
    )
    
    # 直接返回所有话题，不再按评分过滤
    return all_topics if all_topics else [
        HotTopic(topic="护眼健康"),
        HotTopic(topic="配镜攻略"),
        HotTopic(topic="近视防控")
    ]

async def aplan_content_strategy(user_profile: UserProfile, hot_topics: List[HotTopic]) -> ContentStrategy:
    """异步制定内容策略 - 基于增强用户画像"""
    strategy_prompt = CONTENT_STRATEGIST.format(
        user_profile=user_profile.model_dump_json(indent=2),
        hot_topics=[topic.topic for topic in hot_topics]
    )
    
    result = await marvin.generate_async(
        target=ContentStrategy,
        instructions=strategy_prompt,
        n=1,
    )
    
    # 如果返回的是列表，取第一个元素
    if isinstance(result, list):
        if len(result) > 0:
            return result[0]
        else:
            raise ValueError("生成的内容策略为空列表")
    
    return result

async def agenerate_content(
    user_profile: UserProfile,
    hot_topics: List[HotTopic], 
    strategy: ContentStrategy
) -> GeneratedContent:
    """异步生成内容 - 利用丰富用户画像"""
    content_prompt = CONTENT_GENERATOR.format(
        user_profile=user_profile.model_dump_json(indent=2),
        hot_topics=[topic.topic for topic in hot_topics],
        strategy=strategy.model_dump_json()
    )
    
    result = await marvin.generate_async(
        target=GeneratedContent,
        instructions=content_prompt,
        n=1  # 明确指定生成1个实例
    )
    
    # 如果返回的是列表，取第一个元素
    if isinstance(result, list):
        if len(result) > 0:
            return result[0]
        else:
            raise ValueError("生成的内容为空列表")
    
    return result

async def amaintain_content_quality(content: GeneratedContent) -> QualityMaintenance:
    """异步内容质量维护 - 在最少修改的情况下确保符合质量要求"""
    
    result = await marvin.generate_async(
        target=QualityMaintenance,
        instructions=QUALITY_MAINTAINER.format(
            title=content.title,
            content=content.content,
            label=content.label
        ),
        n=1  # 明确指定生成1个实例
    )
    
    # 如果返回的是列表，取第一个元素
    if isinstance(result, list):
        if len(result) > 0:
            return result[0]
        else:
            raise ValueError("生成的质量维护结果为空列表")
    
    return result

async def run_workflow() -> WorkflowResult:
    """运行完整异步工作流"""
    # 步骤1: 异步生成用户画像
    user_profile = await agenerate_user_profile()
    
    # 步骤2: 异步获取并筛选热点话题
    hot_topics = await aextract_hot_topics()
    
    # 步骤3: 异步制定内容策略
    strategy = await aplan_content_strategy(user_profile, hot_topics)
    
    # 步骤4: 异步生成内容
    content = await agenerate_content(user_profile, hot_topics, strategy)
    
    # 步骤5: 异步质量维护
    quality_maintenance = await amaintain_content_quality(content)
    
    return WorkflowResult(
        user_profile=user_profile,
        hot_topics=hot_topics,
        generated_content=content,
        quality_maintenance=quality_maintenance,
        generation_timestamp=datetime.now().isoformat()
    )

# 简单运行代码
if __name__ == "__main__":
    import asyncio
    import marvin
    from pydantic_ai.models.openai import OpenAIModel
    from pydantic_ai.providers.openrouter import OpenRouterProvider

    # 读取配置文件中的API key
    def get_api_key():
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                    api_key = config.get("api_key")
                    if not api_key:
                        raise ValueError("config.json中未找到api_key")
                    return api_key
            else:
                raise FileNotFoundError("config.json文件不存在，请创建配置文件并添加api_key")
        except Exception as e:
            print(f"❌ 读取API key失败: {e}")
            print("请确保config.json文件存在并包含有效的api_key")
            raise e

    model = OpenAIModel(
        'anthropic/claude-sonnet-4',
        provider=OpenRouterProvider(api_key=get_api_key()),
    )
    marvin.defaults.model = model

    async def main():
        try:
            result = await run_workflow()
            
            # 使用异步保存结果到文件
            saved_file = await asave_result_to_file(result)
            
            print(f"✅ 生成完成!")
            print(f"标题: {result.generated_content.title}")
            print(f"内容: {result.generated_content.content}")
            print(f"标签: {', '.join(result.generated_content.label)}")
            print(f"维护后标题: {result.quality_maintenance.title}")
            print(f"维护后内容: {result.quality_maintenance.content}")
            print(f"维护后标签: {', '.join(result.quality_maintenance.label)}")
            print(f"📁 结果已保存到: {saved_file}")
            
        except Exception as e:
            print(f"❌ 执行失败: {e}")
    
    asyncio.run(main())
