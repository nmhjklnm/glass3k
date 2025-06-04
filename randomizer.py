import random
from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class RandomUserConfig:
    """随机用户配置"""
    gender: str
    age_range: str
    vision_type: str
    user_personality: str
    education_level: str
    work_nature: str
    life_pace: str
    
    # 衍生属性（基于合理性约束生成）
    income_level: str
    living_situation: str
    city_tier: str

class UserRandomizer:
    """用户画像随机化器"""
    
    def __init__(self):
        # 核心维度定义
        self.genders = ["男", "女"]
        
        self.age_ranges = [
            "16-18", "19-22", "23-27", "28-35", "36-45", "46-55"
        ]
        
        self.vision_types = [
            "弱视（远视储备过多）",
            "高度近视（600度以上）", 
            "高度散光（200度以上）",
            "度数增长快"
        ]
        
        self.personality_types = [
            "保守谨慎型",  # 决策慢、重视口碑、担心被骗
            "时尚前卫型",  # 追求新潮、注重颜值、愿意尝鲜
            "理性务实型",  # 重视功能、看重性价比、逻辑清晰
            "冲动体验型",  # 决策快、重视感受、容易被感动
            "专业挑剔型",  # 要求高、注重细节、有专业知识
            "社交依赖型"   # 重视他人意见、从众心理、喜欢分享
        ]
        
        self.education_levels = [
            "高中及以下", "大专", "本科", "研究生及以上"
        ]
        
        self.work_natures = [
            "学生", "办公室工作", "户外工作", "创意工作", "服务业"
        ]
        
        self.life_paces = [
            "快节奏", "正常节奏", "慢节奏"
        ]
        
        # 合理性约束映射
        self.education_income_mapping = {
            "高中及以下": ["1000-3000元", "2000-4000元", "3000-5000元"],
            "大专": ["2000-4000元", "3000-5000元", "4000-7000元"],
            "本科": ["3000-5000元", "4000-7000元", "6000-10000元", "8000-15000元"],
            "研究生及以上": ["6000-10000元", "8000-15000元", "12000-25000元", "20000-40000元"]
        }
        
        self.age_education_constraints = {
            "16-18": ["高中及以下"],
            "19-22": ["高中及以下", "大专"],
            "23-27": ["大专", "本科", "研究生及以上"],
            "28-35": ["大专", "本科", "研究生及以上"],
            "36-45": ["高中及以下", "大专", "本科", "研究生及以上"],
            "46-55": ["高中及以下", "大专", "本科", "研究生及以上"]
        }
        
        self.age_work_constraints = {
            "16-18": ["学生"],
            "19-22": ["学生", "服务业", "办公室工作"],
            "23-27": ["办公室工作", "创意工作", "服务业"],
            "28-35": ["办公室工作", "创意工作", "服务业", "户外工作"],
            "36-45": ["办公室工作", "创意工作", "服务业", "户外工作"],
            "46-55": ["办公室工作", "服务业", "户外工作"]
        }

    def generate_random_config(self) -> RandomUserConfig:
        """生成随机用户配置，确保逻辑合理性"""
        
        # 第1步：基础维度随机选择
        gender = random.choice(self.genders)
        age_range = random.choice(self.age_ranges)
        vision_type = random.choice(self.vision_types)
        personality = random.choice(self.personality_types)
        life_pace = random.choice(self.life_paces)
        
        # 第2步：应用年龄约束选择教育背景
        valid_educations = self.age_education_constraints[age_range]
        education = random.choice(valid_educations)
        
        # 第3步：应用年龄约束选择工作性质
        valid_works = self.age_work_constraints[age_range]
        work_nature = random.choice(valid_works)
        
        # 第4步：基于教育背景确定收入水平
        valid_incomes = self.education_income_mapping[education]
        income_level = random.choice(valid_incomes)
        
        # 第5步：生成衍生属性
        living_situation = self._get_living_situation(age_range, income_level)
        city_tier = random.choice(["一线城市", "新一线城市", "二线城市", "三四线城市"])
        
        return RandomUserConfig(
            gender=gender,
            age_range=age_range,
            vision_type=vision_type,
            user_personality=personality,
            education_level=education,
            work_nature=work_nature,
            life_pace=life_pace,
            income_level=income_level,
            living_situation=living_situation,
            city_tier=city_tier
        )
    
    def _get_living_situation(self, age_range: str, income_level: str) -> str:
        """根据年龄和收入确定居住状况"""
        age_start = int(age_range.split('-')[0])
        income_value = self._extract_income_value(income_level)
        
        if age_start <= 22:
            return random.choice(["与父母同住", "学校宿舍"])
        elif age_start <= 27:
            if income_value < 6000:
                return random.choice(["与父母同住", "合租"])
            else:
                return random.choice(["合租", "独居"])
        elif age_start <= 35:
            if income_value < 8000:
                return random.choice(["合租", "独居", "已婚租房"])
            else:
                return random.choice(["独居", "已婚租房", "已婚有房"])
        else:
            if income_value < 10000:
                return random.choice(["已婚租房", "已婚有房"])
            else:
                return random.choice(["已婚有房"])
    
    def _extract_income_value(self, income_range: str) -> int:
        """提取收入范围的中位值"""
        # 从"3000-5000元"中提取4000
        numbers = [int(x) for x in income_range.replace('元', '').split('-')]
        return sum(numbers) // 2
    
    def get_personality_traits(self, personality_type: str) -> Dict[str, List[str]]:
        """根据性格类型返回具体特征"""
        traits_mapping = {
            "保守谨慎型": {
                "decision_style": ["理性对比型"],
                "price_sensitivity": ["价格敏感", "性价比优先"],
                "information_sources": ["百度搜索", "知乎", "朋友推荐", "实体店咨询"],
                "content_preferences": ["科普文章", "对比评测"],
                "concerns": ["被骗风险", "质量问题", "售后保障"]
            },
            "时尚前卫型": {
                "decision_style": ["感性冲动型"],
                "price_sensitivity": ["品质优先", "服务优先"],
                "information_sources": ["小红书", "抖音", "微博", "朋友圈"],
                "content_preferences": ["种草笔记", "美妆搭配"],
                "concerns": ["款式过时", "不够个性", "朋友看法"]
            },
            "理性务实型": {
                "decision_style": ["理性对比型"],
                "price_sensitivity": ["性价比优先"],
                "information_sources": ["专业网站", "产品官网", "技术论坛"],
                "content_preferences": ["技术分析", "功能对比"],
                "concerns": ["功能不足", "性价比低", "技术落后"]
            },
            "冲动体验型": {
                "decision_style": ["感性冲动型"],
                "price_sensitivity": ["服务优先"],
                "information_sources": ["抖音", "快手", "直播平台"],
                "content_preferences": ["短视频", "体验分享"],
                "concerns": ["等待时间长", "体验不好", "后悔购买"]
            },
            "专业挑剔型": {
                "decision_style": ["权威依赖型"],
                "price_sensitivity": ["品质优先"],
                "information_sources": ["专业论坛", "行业报告", "专家推荐"],
                "content_preferences": ["深度分析", "专业评测"],
                "concerns": ["专业度不够", "细节问题", "行业标准"]
            },
            "社交依赖型": {
                "decision_style": ["社交影响型"],
                "price_sensitivity": ["服务优先"],
                "information_sources": ["朋友推荐", "社交平台", "用户评价"],
                "content_preferences": ["用户分享", "社交互动"],
                "concerns": ["朋友不认可", "社交尴尬", "口碑不好"]
            }
        }
        return traits_mapping.get(personality_type, traits_mapping["理性务实型"])

# 全局实例
user_randomizer = UserRandomizer()
