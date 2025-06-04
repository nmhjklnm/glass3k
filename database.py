import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Optional
from pathlib import Path
from contextlib import contextmanager
from task_scheduler import ScheduledTask, TaskStatus, SchedulerConfig
from dataclasses import asdict

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = "data/tasks.db"):
        self.db_path = db_path
        self.ensure_data_dir()
        self.init_database()
    
    def ensure_data_dir(self):
        """确保data目录存在"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 允许通过列名访问
        try:
            yield conn
        finally:
            conn.close()
    
    def init_database(self):
        """初始化数据库表"""
        with self.get_connection() as conn:
            # 创建任务表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    scheduled_time TEXT NOT NULL,
                    workflow_count INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    success_count INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    error_message TEXT
                )
            ''')
            
            # 创建配置表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS scheduler_config (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    auto_create_enabled BOOLEAN DEFAULT 1,
                    auto_create_time TEXT DEFAULT '18:00',
                    auto_execute_delay_hours INTEGER DEFAULT 8,
                    default_workflow_count INTEGER DEFAULT 70,
                    updated_at TEXT NOT NULL
                )
            ''')
            
            # 插入默认配置（如果不存在）
            conn.execute('''
                INSERT OR IGNORE INTO scheduler_config 
                (id, auto_create_enabled, auto_create_time, auto_execute_delay_hours, default_workflow_count, updated_at)
                VALUES (1, 1, '18:00', 8, 70, ?)
            ''', (datetime.now().isoformat(),))
            
            conn.commit()
    
    def save_task(self, task: ScheduledTask) -> bool:
        """保存或更新任务"""
        try:
            with self.get_connection() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO scheduled_tasks 
                    (id, name, scheduled_time, workflow_count, status, created_at, 
                     started_at, completed_at, success_count, error_count, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task.id, task.name, task.scheduled_time, task.workflow_count,
                    task.status.value, task.created_at, task.started_at, task.completed_at,
                    task.success_count, task.error_count, task.error_message
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"保存任务失败: {e}")
            return False
    
    def load_tasks(self) -> List[ScheduledTask]:
        """加载所有任务"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM scheduled_tasks 
                    ORDER BY created_at DESC
                ''')
                
                tasks = []
                for row in cursor:
                    task = ScheduledTask(
                        id=row['id'],
                        name=row['name'],
                        scheduled_time=row['scheduled_time'],
                        workflow_count=row['workflow_count'],
                        status=TaskStatus(row['status']),
                        created_at=row['created_at'],
                        started_at=row['started_at'],
                        completed_at=row['completed_at'],
                        success_count=row['success_count'] or 0,
                        error_count=row['error_count'] or 0,
                        error_message=row['error_message']
                    )
                    tasks.append(task)
                
                return tasks
        except Exception as e:
            print(f"加载任务失败: {e}")
            return []
    
    def get_task_by_id(self, task_id: str) -> Optional[ScheduledTask]:
        """根据ID获取任务"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    'SELECT * FROM scheduled_tasks WHERE id = ?', 
                    (task_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    return ScheduledTask(
                        id=row['id'],
                        name=row['name'],
                        scheduled_time=row['scheduled_time'],
                        workflow_count=row['workflow_count'],
                        status=TaskStatus(row['status']),
                        created_at=row['created_at'],
                        started_at=row['started_at'],
                        completed_at=row['completed_at'],
                        success_count=row['success_count'] or 0,
                        error_count=row['error_count'] or 0,
                        error_message=row['error_message']
                    )
        except Exception as e:
            print(f"获取任务失败: {e}")
        
        return None
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        try:
            with self.get_connection() as conn:
                conn.execute('DELETE FROM scheduled_tasks WHERE id = ?', (task_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"删除任务失败: {e}")
            return False
    
    def delete_old_tasks(self, days: int = 30) -> int:
        """删除N天前的已完成任务"""
        try:
            # 修复：使用timedelta正确计算N天前的日期
            cutoff_date = datetime.now() - timedelta(days=days)
            cutoff_str = cutoff_date.isoformat()
            
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    DELETE FROM scheduled_tasks 
                    WHERE status IN ('已完成', '失败', '已取消')
                    AND (completed_at < ? OR (completed_at IS NULL AND created_at < ?))
                ''', (cutoff_str, cutoff_str))
                
                deleted_count = cursor.rowcount
                conn.commit()
                return deleted_count
        except Exception as e:
            print(f"清理旧任务失败: {e}")
            return 0
    
    def save_config(self, config: SchedulerConfig) -> bool:
        """保存配置"""
        try:
            with self.get_connection() as conn:
                conn.execute('''
                    UPDATE scheduler_config SET
                    auto_create_enabled = ?,
                    auto_create_time = ?,
                    auto_execute_delay_hours = ?,
                    default_workflow_count = ?,
                    updated_at = ?
                    WHERE id = 1
                ''', (
                    config.auto_create_enabled,
                    config.auto_create_time,
                    config.auto_execute_delay_hours,
                    config.default_workflow_count,
                    datetime.now().isoformat()
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
    
    def load_config(self) -> SchedulerConfig:
        """加载配置"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('SELECT * FROM scheduler_config WHERE id = 1')
                row = cursor.fetchone()
                
                if row:
                    return SchedulerConfig(
                        auto_create_enabled=bool(row['auto_create_enabled']),
                        auto_create_time=row['auto_create_time'],
                        auto_execute_delay_hours=row['auto_execute_delay_hours'],
                        default_workflow_count=row['default_workflow_count']
                    )
        except Exception as e:
            print(f"加载配置失败: {e}")
        
        # 返回默认配置
        return SchedulerConfig()
    
    def get_task_statistics(self) -> dict:
        """获取任务统计信息"""
        try:
            with self.get_connection() as conn:
                # 总任务数
                cursor = conn.execute('SELECT COUNT(*) as total FROM scheduled_tasks')
                total = cursor.fetchone()['total']
                
                # 按状态统计
                cursor = conn.execute('''
                    SELECT status, COUNT(*) as count 
                    FROM scheduled_tasks 
                    GROUP BY status
                ''')
                status_counts = {row['status']: row['count'] for row in cursor}
                
                # 修复：最近7天的任务 - 使用timedelta正确计算
                week_ago = datetime.now() - timedelta(days=7)
                week_ago_str = week_ago.isoformat()
                
                cursor = conn.execute('''
                    SELECT COUNT(*) as recent 
                    FROM scheduled_tasks 
                    WHERE created_at >= ?
                ''', (week_ago_str,))
                recent = cursor.fetchone()['recent']
                
                return {
                    'total_tasks': total,
                    'status_counts': status_counts,
                    'recent_tasks': recent
                }
        except Exception as e:
            print(f"获取统计信息失败: {e}")
            return {
                'total_tasks': 0,
                'status_counts': {},
                'recent_tasks': 0
            }
    
    def migrate_from_json(self, json_file: str) -> bool:
        """从JSON文件迁移数据到数据库"""
        try:
            if not Path(json_file).exists():
                return True
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            migrated_count = 0
            for task_data in data:
                task = ScheduledTask(
                    id=task_data['id'],
                    name=task_data['name'],
                    scheduled_time=task_data['scheduled_time'],
                    workflow_count=task_data['workflow_count'],
                    status=TaskStatus(task_data['status']),
                    created_at=task_data['created_at'],
                    started_at=task_data.get('started_at'),
                    completed_at=task_data.get('completed_at'),
                    success_count=task_data.get('success_count', 0),
                    error_count=task_data.get('error_count', 0),
                    error_message=task_data.get('error_message')
                )
                
                if self.save_task(task):
                    migrated_count += 1
            
            print(f"成功迁移 {migrated_count} 个任务到数据库")
            
            # 备份原文件
            backup_file = f"{json_file}.backup"
            Path(json_file).rename(backup_file)
            print(f"原JSON文件已备份为: {backup_file}")
            
            return True
            
        except Exception as e:
            print(f"迁移数据失败: {e}")
            return False

# 全局数据库管理器实例
db_manager = DatabaseManager()
