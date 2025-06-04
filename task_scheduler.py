import json
import schedule
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
import os
from pathlib import Path

class TaskStatus(Enum):
    PENDING = "待运行"
    RUNNING = "运行中"
    COMPLETED = "已完成"
    FAILED = "失败"
    CANCELLED = "已取消"

@dataclass
class ScheduledTask:
    id: str
    name: str
    scheduled_time: str  # "02:00"
    workflow_count: int
    status: TaskStatus
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    success_count: int = 0
    error_count: int = 0
    error_message: Optional[str] = None

@dataclass
class SchedulerConfig:
    """调度器配置"""
    auto_create_enabled: bool = True
    auto_create_time: str = "18:00"
    auto_execute_delay_hours: int = 8  # 改为小时延迟，默认8小时后执行
    default_workflow_count: int = 70

class TaskScheduler:
    def __init__(self):
        # 移除JSON文件相关配置
        self.scheduler_thread = None
        self.is_running = False
        self.current_task_id = None
        self.config = SchedulerConfig()
        
        # 初始化数据库
        from database import db_manager
        self.db = db_manager
        
        # 尝试从旧JSON文件迁移数据
        self._migrate_from_json()
        
        # 加载配置
        self.load_config()
        
    def _migrate_from_json(self):
        """从JSON文件迁移到数据库"""
        json_tasks_file = "data/scheduled_tasks.json"
        json_config_file = "data/scheduler_config.json"
        
        # 迁移任务数据
        if os.path.exists(json_tasks_file):
            self.db.migrate_from_json(json_tasks_file)
        
        # 迁移配置数据
        if os.path.exists(json_config_file):
            try:
                with open(json_config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                old_config = SchedulerConfig(
                    auto_create_enabled=config_data.get('auto_create_enabled', True),
                    auto_create_time=config_data.get('auto_create_time', "18:00"),
                    auto_execute_delay_hours=config_data.get('auto_execute_delay_hours', 8),
                    default_workflow_count=config_data.get('default_workflow_count', 70)
                )
                
                self.db.save_config(old_config)
                
                # 备份配置文件
                backup_file = f"{json_config_file}.backup"
                Path(json_config_file).rename(backup_file)
                print(f"配置文件已备份为: {backup_file}")
                
            except Exception as e:
                print(f"迁移配置失败: {e}")
        
    def load_config(self) -> SchedulerConfig:
        """加载调度器配置"""
        self.config = self.db.load_config()
        return self.config
    
    def save_config(self):
        """保存调度器配置"""
        return self.db.save_config(self.config)
    
    def update_config(self, **kwargs):
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        self.save_config()
        
        # 重新设置调度器
        if self.is_running:
            self.stop_scheduler()
            self.start_scheduler()
    
    def load_tasks(self) -> List[ScheduledTask]:
        """加载任务列表"""
        return self.db.load_tasks()
    
    def save_tasks(self, tasks: List[ScheduledTask]):
        """保存任务列表（兼容性方法，现在逐个保存）"""
        for task in tasks:
            self.db.save_task(task)
    
    def create_daily_task(self, workflow_count: int = None) -> ScheduledTask:
        """创建定时任务"""
        if workflow_count is None:
            workflow_count = self.config.default_workflow_count
        
        # 计算执行时间：当前时间 + 延迟小时数
        execute_time = datetime.now() + timedelta(hours=self.config.auto_execute_delay_hours)
        task_id = f"task_{execute_time.strftime('%Y%m%d_%H%M')}"
        
        task = ScheduledTask(
            id=task_id,
            name=f"定时任务 - {execute_time.strftime('%m月%d日 %H:%M')}",
            scheduled_time=execute_time.strftime('%H:%M'),
            workflow_count=workflow_count,
            status=TaskStatus.PENDING,
            created_at=datetime.now().isoformat()
        )
        
        # 保存到数据库
        if self.db.save_task(task):
            return task
        else:
            raise Exception("保存任务到数据库失败")
    
    def create_immediate_task(self, workflow_count: int = None) -> ScheduledTask:
        """创建立即执行的测试任务"""
        if workflow_count is None:
            workflow_count = 5  # 测试任务默认5次
        
        # 立即执行：当前时间 + 1分钟
        execute_time = datetime.now() + timedelta(minutes=1)
        task_id = f"test_{execute_time.strftime('%Y%m%d_%H%M%S')}"
        
        task = ScheduledTask(
            id=task_id,
            name=f"测试任务 - {execute_time.strftime('%H:%M:%S')}",
            scheduled_time=execute_time.strftime('%H:%M'),
            workflow_count=workflow_count,
            status=TaskStatus.PENDING,
            created_at=datetime.now().isoformat()
        )
        
        # 保存到数据库
        if self.db.save_task(task):
            return task
        else:
            raise Exception("保存测试任务到数据库失败")
    
    def execute_task_immediately(self, task_id: str):
        """立即执行指定任务（异步）"""
        def run_task():
            asyncio.run(self.execute_task(task_id))
        
        task_thread = threading.Thread(target=run_task, daemon=True)
        task_thread.start()
        print(f"立即开始执行任务: {task_id}")
    
    def get_tasks(self) -> Dict[str, List[ScheduledTask]]:
        """获取分类的任务列表"""
        tasks = self.load_tasks()
        
        pending_tasks = [t for t in tasks if t.status == TaskStatus.PENDING]
        running_tasks = [t for t in tasks if t.status == TaskStatus.RUNNING]
        completed_tasks = [t for t in tasks if t.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]]
        
        return {
            "pending": pending_tasks,
            "running": running_tasks,
            "completed": completed_tasks
        }
    
    def update_task_status(self, task_id: str, status: TaskStatus, **kwargs):
        """更新任务状态"""
        task = self.db.get_task_by_id(task_id)
        if not task:
            print(f"任务 {task_id} 不存在")
            return
        
        task.status = status
        
        if status == TaskStatus.RUNNING:
            task.started_at = datetime.now().isoformat()
        elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            task.completed_at = datetime.now().isoformat()
            task.success_count = kwargs.get('success_count', 0)
            task.error_count = kwargs.get('error_count', 0)
            task.error_message = kwargs.get('error_message')
        
        self.db.save_task(task)
    
    def cancel_task(self, task_id: str):
        """取消任务"""
        self.update_task_status(task_id, TaskStatus.CANCELLED)
    
    def delete_task(self, task_id: str):
        """删除任务"""
        return self.db.delete_task(task_id)
    
    def clean_old_tasks(self, days: int = 30) -> int:
        """清理旧任务"""
        return self.db.delete_old_tasks(days)
    
    def get_task_statistics(self) -> dict:
        """获取任务统计信息"""
        return self.db.get_task_statistics()
    
    async def execute_task(self, task_id: str):
        """执行任务"""
        from workflow import run_workflow
        from utils import asave_result_to_file
        
        self.current_task_id = task_id
        self.update_task_status(task_id, TaskStatus.RUNNING)
        
        tasks = self.load_tasks()
        task = next((t for t in tasks if t.id == task_id), None)
        
        if not task:
            return
        
        success_count = 0
        error_count = 0
        error_messages = []
        
        try:
            for i in range(task.workflow_count):
                try:
                    result = await run_workflow()
                    await asave_result_to_file(result)
                    success_count += 1
                    print(f"任务 {task_id}: 第 {i+1}/{task.workflow_count} 次执行成功")
                except Exception as e:
                    error_count += 1
                    error_messages.append(f"第{i+1}次: {str(e)}")
                    print(f"任务 {task_id}: 第 {i+1}/{task.workflow_count} 次执行失败: {e}")
                
                # 添加延迟
                await asyncio.sleep(0.5)
            
            # 任务完成
            status = TaskStatus.COMPLETED if error_count == 0 else TaskStatus.FAILED
            error_msg = "; ".join(error_messages[:3]) if error_messages else None
            
            self.update_task_status(
                task_id, 
                status, 
                success_count=success_count,
                error_count=error_count,
                error_message=error_msg
            )
            
        except Exception as e:
            self.update_task_status(
                task_id, 
                TaskStatus.FAILED,
                error_message=str(e)
            )
        finally:
            self.current_task_id = None
    
    def start_scheduler(self):
        """启动调度器"""
        if self.is_running:
            return
        
        # 清空现有调度
        schedule.clear()
        
        # 只有在启用自动创建时才设置自动创建任务
        if self.config.auto_create_enabled:
            schedule.every().day.at(self.config.auto_create_time).do(self._auto_create_task)
        
        # 设置任务执行检查（每分钟检查一次是否有任务需要执行）
        schedule.every().minute.do(self._check_and_execute_tasks)
        
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        print(f"调度器已启动:")
        print(f"  - 自动创建任务: {'启用' if self.config.auto_create_enabled else '禁用'}")
        if self.config.auto_create_enabled:
            print(f"  - 创建时间: {self.config.auto_create_time}")
        print(f"  - 执行延迟: {self.config.auto_execute_delay_hours}小时后")
    
    def stop_scheduler(self):
        """停止调度器"""
        self.is_running = False
        schedule.clear()
        print("调度器已停止")
    
    def _run_scheduler(self):
        """调度器主循环"""
        while self.is_running:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    
    def _auto_create_task(self):
        """自动创建任务"""
        try:
            if self.config.auto_create_enabled:
                task = self.create_daily_task()
                print(f"自动创建定时任务成功: {task.name} (将在{self.config.auto_execute_delay_hours}小时后执行)")
            else:
                print("自动创建任务已禁用，跳过创建")
        except Exception as e:
            print(f"自动创建任务失败: {e}")
    
    def _check_and_execute_tasks(self):
        """检查并执行到时的任务"""
        try:
            tasks = self.get_tasks()
            current_time = datetime.now()
            
            for task in tasks['pending']:
                # 解析任务的预定执行时间
                task_created_time = datetime.fromisoformat(task.created_at)
                
                # 判断是否为测试任务（立即执行）
                if task.id.startswith('test_'):
                    # 测试任务：创建1分钟后执行
                    task_execute_time = task_created_time + timedelta(minutes=1)
                else:
                    # 普通任务：按配置延迟执行
                    task_execute_time = task_created_time + timedelta(hours=self.config.auto_execute_delay_hours)
                
                # 如果当前时间已经到达或超过任务执行时间
                if current_time >= task_execute_time:
                    # 在新线程中执行异步任务
                    def run_task():
                        asyncio.run(self.execute_task(task.id))
                    
                    task_thread = threading.Thread(target=run_task, daemon=True)
                    task_thread.start()
                    print(f"开始执行定时任务: {task.name}")
                    break  # 一次只执行一个任务
        except Exception as e:
            print(f"检查和执行任务失败: {e}")

# 全局调度器实例
task_scheduler = TaskScheduler()
