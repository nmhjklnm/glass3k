from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum

class UserProfile(BaseModel):
    """目标用户画像 - 增强版"""
    # 基础人口统计信息
    gender: Literal["男", "女"] = Field(description="性别")
    age: int = Field(ge=16, le=55, description="具体年龄")
    profile_type: Literal["弱视（远视储备过多）", "高度近视（600度以上）", "高度散光（200度以上）", "度数增长快"]
    age_group: Literal["在校学生", "职场新人", "资深白领", "关爱家长"]
    
    # 地理和社会经济维度
    education_level: Literal["高中及以下", "大专", "本科", "研究生及以上"] = Field(description="教育背景")
    monthly_income: str = Field(description="月收入范围，如'3000-5000元'")
    living_situation: Literal["与父母同住", "合租", "独居", "已婚有房", "已婚租房"] = Field(description="居住状况")
    
    # 生活方式和习惯
    work_intensity: Literal["高强度加班", "正常8小时", "相对轻松", "学生作息"] = Field(description="工作/学习强度")
    screen_time: str = Field(description="每日屏幕使用时长，如'8小时以上'")
    exercise_habit: Literal["经常运动", "偶尔运动", "很少运动", "不运动"] = Field(description="运动习惯")
    sleep_quality: Literal["很好", "一般", "较差", "很差"] = Field(description="睡眠质量")
    
    # 消费心理和行为
    purchase_decision_style: Literal["理性对比型", "感性冲动型", "权威依赖型", "社交影响型"] = Field(description="购买决策风格")
    price_sensitivity: Literal["价格敏感", "性价比优先", "品质优先", "服务优先"] = Field(description="价格敏感度")
    information_source: List[str] = Field(description="信息获取渠道", min_items=2, max_items=4)
    social_influence: Literal["很在意他人看法", "比较在意", "不太在意", "完全不在意"] = Field(description="社交影响程度")
    
    # 具体痛点和需求
    pain_points: List[str] = Field(description="具体生活场景痛点", min_items=3, max_items=5)
    purchase_triggers: List[str] = Field(description="购买触发因素", min_items=2, max_items=4)
    
    # 兴趣和生活偏好
    interests: List[str] = Field(description="兴趣话题", min_items=4, max_items=6)
    content_preference: List[str] = Field(description="内容偏好类型", min_items=2, max_items=3)
    
    # 个性特征（增加真实感）
    personality_traits: List[str] = Field(description="性格特点/小缺陷", min_items=2, max_items=3)
    concerns_anxieties: List[str] = Field(description="担忧和焦虑点", min_items=2, max_items=3)

class HotTopic(BaseModel):
    """热点话题"""
    topic: str = Field(description="话题内容")

class ContentStrategy(BaseModel):
    """内容策略组合"""
    effect_type: Literal["度数下降", "度数稳定"]
    trust_building: Literal["推荐介绍", "老客户复购", "排队验光", "家族传承"]
    value_proposition: List[str] = Field(description="选中的产品/服务优势")
    product_highlight: str = Field(description="重点推荐的产品组合")
    price_expression: str = Field(description="价格模糊量化表达方式")
    experience_point: str = Field(description="体验亮点")

class GeneratedContent(BaseModel):
    """生成的内容"""
    title: str = Field(max_length=20, description="标题，20字以内")
    content: str = Field(min_length=50, max_length=500, description="正文内容")
    label: List[str] = Field(description="话题标签，共9个", min_items=9, max_items=9)

class QualityMaintenance(BaseModel):
    """质量维护结果"""
    title: str = Field(max_length=20, description="维护后的标题，20字以内")
    content: str = Field(min_length=50, max_length=400, description="维护后的正文内容")
    label: List[str] = Field(description="维护后的话题标签，共9个", min_items=9, max_items=9)

class WorkflowResult(BaseModel):
    """工作流最终结果"""
    user_profile: UserProfile
    hot_topics: List[HotTopic]
    generated_content: GeneratedContent
    quality_maintenance: QualityMaintenance
    generation_timestamp: str
