import streamlit as st
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
import threading
import time
import os
import zipfile
import io

# 导入任务调度器
try:
    from task_scheduler import task_scheduler, TaskStatus
except ImportError:
    st.error("无法导入任务调度器，请检查 task_scheduler.py 文件")
    st.stop()

def create_download_zip():
    """创建包含所有txt文件的ZIP包"""
    data_dir = Path("data")
    if not data_dir.exists():
        return None
    
    files = list(data_dir.glob("result_*.txt"))
    if not files:
        return None
    
    # 创建内存中的ZIP文件
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file in files:
            # 添加文件到ZIP，使用相对路径
            zip_file.write(file, file.name)
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def delete_all_txt_files():
    """删除所有生成的txt文件"""
    data_dir = Path("data")
    if not data_dir.exists():
        return 0
    
    files = list(data_dir.glob("result_*.txt"))
    deleted_count = 0
    
    for file in files:
        try:
            file.unlink()
            deleted_count += 1
        except Exception as e:
            st.error(f"删除文件 {file.name} 失败: {e}")
    
    return deleted_count

def show_generated_files():
    """显示生成的文件"""
    st.subheader("📋 生成文件管理")
    
    data_dir = Path("data")
    if not data_dir.exists():
        st.info("data 目录不存在，暂无生成文件")
        return
    
    files = sorted(data_dir.glob("result_*.txt"), key=os.path.getctime, reverse=True)
    
    if not files:
        st.info("暂无生成文件")
        return
    
    # 文件统计信息
    total_files = len(files)
    total_size_bytes = sum(f.stat().st_size for f in files)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("文件总数", total_files)
    with col2:
        st.metric("总大小", f"{total_size_bytes / 1024:.1f} KB")
    with col3:
        if files:
            latest_file = max(files, key=os.path.getctime)
            latest_time = datetime.fromtimestamp(os.path.getctime(latest_file))
            st.metric("最新文件", latest_time.strftime("%H:%M:%S"))
    with col4:
        # 刷新按钮
        if st.button("🔄 刷新", help="重新加载文件列表"):
            st.rerun()
    
    # 文件操作按钮
    if total_files > 0:
        col1, col2 = st.columns(2)
        
        with col1:
            zip_data = create_download_zip()
            if zip_data:
                st.download_button(
                    label="📦 下载所有文件",
                    data=zip_data,
                    file_name=f"glass3k_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    mime="application/zip",
                    use_container_width=True
                )
        
        with col2:
            if st.button("🗑️ 删除所有文件", use_container_width=True, type="secondary"):
                deleted_count = delete_all_txt_files()
                if deleted_count > 0:
                    st.success(f"✅ 已删除 {deleted_count} 个文件")
                    st.rerun()
                else:
                    st.info("没有文件需要删除")
    
    st.markdown("---")
    
    # 文件列表
    with st.expander("📄 文件详情列表", expanded=False):
        for i, file in enumerate(files[:20]):  # 显示最近20个文件
            file_time = datetime.fromtimestamp(os.path.getctime(file))
            file_size = os.path.getsize(file)
            
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2.5, 1.5, 1, 0.8, 0.8])
                
                with col1:
                    st.text(f"📄 {file.name}")
                with col2:
                    st.text(f"⏰ {file_time.strftime('%m-%d %H:%M:%S')}")
                with col3:
                    st.text(f"📏 {file_size} B")
                with col4:
                    if st.button("👁️", key=f"preview_{file.name}_{i}", help="预览文件"):
                        try:
                            with open(file, 'r', encoding='utf-8') as f:
                                content = f.read()
                            st.text_area(
                                f"文件内容预览 - {file.name}", 
                                content, 
                                height=200, 
                                key=f"content_{file.name}_{i}"
                            )
                        except Exception as e:
                            st.error(f"读取文件失败: {e}")
                with col5:
                    # 删除单个文件按钮
                    if st.button("🗑️", key=f"delete_{file.name}_{i}", help="删除此文件"):
                        try:
                            file.unlink()
                            st.success(f"✅ 已删除 {file.name}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"删除文件失败: {e}")
                
                if i < min(len(files), 20) - 1:
                    st.divider()

def main():
    st.set_page_config(
        page_title="定时任务管理",
        page_icon="📅",
        layout="wide"
    )
    
    st.title("📅 定时任务管理")
    st.markdown("---")
    
    # 启动调度器
    if not task_scheduler.is_running:
        task_scheduler.start_scheduler()
    
    # 侧边栏控制面板
    with st.sidebar:
        st.header("⚙️ 任务控制")
        
        # 自动创建任务配置
        st.subheader("🔧 自动化配置")
        
        # 自动创建开关
        auto_create_enabled = st.checkbox(
            "🕕 启用自动创建任务",
            value=task_scheduler.config.auto_create_enabled,
            help="每天下午6点自动创建明天的任务"
        )
        
        # 只有在启用自动创建时才显示相关配置
        if auto_create_enabled:
            col1, col2 = st.columns(2)
            with col1:
                auto_create_time = st.time_input(
                    "创建时间",
                    value=datetime.strptime(task_scheduler.config.auto_create_time, "%H:%M").time(),
                    help="每天自动创建任务的时间"
                )
            
            with col2:
                default_count = st.number_input(
                    "默认次数",
                    min_value=1,
                    max_value=200,
                    value=task_scheduler.config.default_workflow_count,
                    help="自动创建任务的默认执行次数"
                )
        else:
            auto_create_time = datetime.strptime(task_scheduler.config.auto_create_time, "%H:%M").time()
            default_count = task_scheduler.config.default_workflow_count
        
        # 执行延迟配置
        execute_delay_hours = st.number_input(
            "执行延迟(小时)",
            min_value=1,
            max_value=72,
            value=task_scheduler.config.auto_execute_delay_hours,
            help="任务创建后多少小时后开始执行"
        )
        
        # 保存配置按钮
        if st.button("💾 保存配置", use_container_width=True):
            task_scheduler.update_config(
                auto_create_enabled=auto_create_enabled,
                auto_create_time=auto_create_time.strftime("%H:%M"),
                auto_execute_delay_hours=execute_delay_hours,
                default_workflow_count=default_count
            )
            st.success("✅ 配置已保存并生效！")
            st.rerun()
        
        st.markdown("---")
        
        # 手动创建任务
        st.subheader("➕ 手动创建任务")
        workflow_count = st.number_input(
            "执行次数",
            min_value=1,
            max_value=200,
            value=task_scheduler.config.default_workflow_count,
            help=f"设置{execute_delay_hours}小时后执行的workflow次数"
        )
        
        if st.button("🕐 创建任务", use_container_width=True, type="primary"):
            try:
                task = task_scheduler.create_daily_task(workflow_count)
                execute_time = datetime.now() + timedelta(hours=execute_delay_hours)
                st.success(f"✅ 已创建任务: {task.name}")
                st.info(f"⏰ 将在 {execute_time.strftime('%m月%d日 %H:%M')} 执行")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 创建任务失败: {e}")
        
        st.markdown("---")
        
        # 调度器状态
        st.subheader("📊 调度器状态")
        
        # 运行状态
        status_color = "🟢" if task_scheduler.is_running else "🔴"
        st.text(f"{status_color} {'运行中' if task_scheduler.is_running else '已停止'}")
        
        # 自动创建状态
        auto_status = "🟢 启用" if task_scheduler.config.auto_create_enabled else "🔴 禁用"
        st.text(f"自动创建: {auto_status}")
        
        if task_scheduler.config.auto_create_enabled:
            st.caption(f"⏰ 每天 {task_scheduler.config.auto_create_time} 自动创建")
        
        st.caption(f"⚡ 创建后 {task_scheduler.config.auto_execute_delay_hours} 小时后执行")
        
        # 控制按钮
        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ 启动", disabled=task_scheduler.is_running):
                task_scheduler.start_scheduler()
                st.success("调度器已启动")
                st.rerun()
        
        with col2:
            if st.button("⏹️ 停止", disabled=not task_scheduler.is_running):
                task_scheduler.stop_scheduler()
                st.warning("调度器已停止")
                st.rerun()
        
        st.markdown("---")
        
        # 数据库状态
        st.subheader("💾 数据库状态")
        
        try:
            stats = task_scheduler.get_task_statistics()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("总任务数", stats['total_tasks'])
            with col2:
                st.metric("最近7天", stats['recent_tasks'])
            
            # 状态分布
            if stats['status_counts']:
                st.write("**状态分布:**")
                for status, count in stats['status_counts'].items():
                    st.text(f"{status}: {count}")
            
            # 数据库文件信息
            db_file = Path("data/tasks.db")
            if db_file.exists():
                size_mb = db_file.stat().st_size / 1024 / 1024
                st.caption(f"数据库大小: {size_mb:.2f} MB")
            
        except Exception as e:
            st.error(f"获取数据库状态失败: {e}")
        
        # 数据库管理
        with st.expander("🔧 数据库管理"):
            if st.button("🗑️ 清理30天前任务", use_container_width=True):
                deleted_count = task_scheduler.clean_old_tasks(30)
                if deleted_count > 0:
                    st.success(f"✅ 已清理 {deleted_count} 个旧任务")
                else:
                    st.info("没有需要清理的任务")
                st.rerun()
            
            if st.button("📊 重新统计", use_container_width=True):
                st.rerun()
            
            # 数据备份下载
            try:
                import sqlite3
                import io
                
                if st.button("📥 备份数据库", use_container_width=True):
                    db_file = "data/tasks.db"
                    if os.path.exists(db_file):
                        with open(db_file, 'rb') as f:
                            db_data = f.read()
                        
                        st.download_button(
                            label="⬇️ 下载数据库备份",
                            data=db_data,
                            file_name=f"tasks_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
                            mime="application/octet-stream",
                            use_container_width=True
                        )
            except Exception as e:
                st.error(f"备份功能异常: {e}")
        
        st.markdown("---")
        
        # 快速操作
        st.subheader("🔧 快速操作")
        if st.button("🔄 刷新页面", use_container_width=True):
            st.rerun()
        
        # 清理旧任务
        if st.button("🗑️ 清理旧任务", use_container_width=True):
            clean_old_tasks()
            st.success("旧任务已清理")
            st.rerun()
        
        # 测试功能区域
        st.markdown("---")
        st.subheader("🧪 测试功能")
        
        # 立即执行测试
        test_count = st.number_input(
            "测试执行次数",
            min_value=1,
            max_value=20,
            value=3,
            help="创建立即执行的测试任务"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("⚡ 立即执行测试", use_container_width=True, type="secondary"):
                try:
                    test_task = task_scheduler.create_immediate_task(test_count)
                    st.success(f"✅ 测试任务已创建: {test_task.name}")
                    st.info("⏰ 任务将在1分钟后开始执行")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 创建测试任务失败: {e}")
        
        with col2:
            if st.button("🕐 创建定时任务", use_container_width=True):
                try:
                    task = task_scheduler.create_daily_task(workflow_count)
                    execute_time = datetime.now() + timedelta(hours=task_scheduler.config.auto_execute_delay_hours)
                    st.success(f"✅ 已创建任务: {task.name}")
                    st.info(f"⏰ 将在 {execute_time.strftime('%m月%d日 %H:%M')} 执行")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 创建任务失败: {e}")
    
    # 主界面 - 任务列表和文件管理
    tasks = task_scheduler.get_tasks()
    
    # 创建标签页
    tab1, tab2, tab3, tab4 = st.tabs([
        f"⏳ 待运行 ({len(tasks['pending'])})",
        f"▶️ 运行中 ({len(tasks['running'])})", 
        f"✅ 已完成 ({len(tasks['completed'])})",
        "📁 文件管理"
    ])
    
    with tab1:
        show_pending_tasks(tasks['pending'])
    
    with tab2:
        show_running_tasks(tasks['running'])
    
    with tab3:
        show_completed_tasks(tasks['completed'])
    
    with tab4:
        show_generated_files()

def show_pending_tasks(tasks):
    """显示待运行任务"""
    st.subheader("⏳ 待运行任务")
    
    if not tasks:
        st.info("📋 暂无待运行任务")
        
        # 显示下次自动创建时间提示
        if task_scheduler.config.auto_create_enabled:
            now = datetime.now()
            tomorrow_create_time = datetime.combine(
                now.date() + timedelta(days=1),
                datetime.strptime(task_scheduler.config.auto_create_time, "%H:%M").time()
            )
            
            # 如果今天的创建时间还没过，则是今天
            today_create_time = datetime.combine(
                now.date(),
                datetime.strptime(task_scheduler.config.auto_create_time, "%H:%M").time()
            )
            
            if now < today_create_time:
                next_create_time = today_create_time
            else:
                next_create_time = tomorrow_create_time
            
            next_execute_time = next_create_time + timedelta(hours=task_scheduler.config.auto_execute_delay_hours)
            
            time_diff = next_execute_time - now
            hours = int(time_diff.total_seconds() // 3600)
            minutes = int((time_diff.total_seconds() % 3600) // 60)
            
            st.info(f"💡 系统将在 {hours}小时{minutes}分钟后执行下一个自动创建的任务")
        else:
            st.warning("⚠️ 自动创建任务已禁用，请手动创建或在侧边栏启用自动创建")
        
        return
    
    for task in tasks:
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            
            with col1:
                # 显示任务类型
                if task.id.startswith('test_'):
                    task_type = "🧪 测试任务"
                else:
                    task_type = "⏰ 定时任务"
                
                st.write(f"**{task_type}**")
                st.write(f"{task.name}")
                st.caption(f"📅 创建时间: {format_datetime(task.created_at)}")
            
            with col2:
                st.write(f"🎯 {task.workflow_count} 次")
                st.caption("执行次数")
            
            with col3:
                # 计算距离执行时间
                now = datetime.now()
                task_created_time = datetime.fromisoformat(task.created_at)
                
                # 根据任务类型计算执行时间
                if task.id.startswith('test_'):
                    task_execute_time = task_created_time + timedelta(minutes=1)
                else:
                    task_execute_time = task_created_time + timedelta(hours=task_scheduler.config.auto_execute_delay_hours)
                
                time_diff = task_execute_time - now
                
                if time_diff.total_seconds() > 0:
                    if task.id.startswith('test_'):
                        # 测试任务显示秒数
                        seconds = int(time_diff.total_seconds())
                        if seconds > 60:
                            minutes = seconds // 60
                            seconds = seconds % 60
                            st.write(f"⏰ {minutes}分{seconds}秒后")
                        else:
                            st.write(f"⏰ {seconds}秒后")
                    else:
                        # 普通任务显示小时分钟
                        hours = int(time_diff.total_seconds() // 3600)
                        minutes = int((time_diff.total_seconds() % 3600) // 60)
                        
                        if hours > 0:
                            st.write(f"⏰ {hours}小时{minutes}分钟后")
                        else:
                            st.write(f"⏰ {minutes}分钟后")
                    
                    st.caption("距离执行时间")
                else:
                    st.write("⏰ 即将执行")
                    st.caption("等待执行中")
            
            with col4:
                # 操作按钮
                col_cancel, col_execute = st.columns(2)
                
                with col_cancel:
                    if st.button("❌", key=f"cancel_{task.id}", help="取消任务"):
                        task_scheduler.cancel_task(task.id)
                        st.success("任务已取消")
                        st.rerun()
                
                with col_execute:
                    # 立即执行按钮（仅对测试任务显示）
                    if task.id.startswith('test_'):
                        if st.button("⚡", key=f"execute_{task.id}", help="立即执行"):
                            task_scheduler.execute_task_immediately(task.id)
                            st.success("任务已开始执行")
                            st.rerun()
            
            st.divider()

def show_running_tasks(tasks):
    """显示运行中任务"""
    st.subheader("▶️ 运行中任务")
    
    if not tasks:
        st.info("📋 暂无运行中任务")
        return
    
    for task in tasks:
        with st.container():
            col1, col2, col3 = st.columns([4, 2, 2])
            
            with col1:
                st.write(f"**{task.name}**")
                st.caption(f"🚀 开始时间: {format_datetime(task.started_at)}")
                
                # 显示进度条（模拟）
                if task.id == task_scheduler.current_task_id:
                    progress_placeholder = st.empty()
                    # 这里可以添加实际进度跟踪
                    with progress_placeholder:
                        st.progress(0.5, "执行中...")
            
            with col2:
                st.write(f"🎯 {task.workflow_count} 次")
                st.caption("目标执行次数")
            
            with col3:
                # 运行时间计算
                if task.started_at:
                    start_time = datetime.fromisoformat(task.started_at)
                    running_time = datetime.now() - start_time
                    minutes = int(running_time.total_seconds() // 60)
                    st.write(f"⏱️ {minutes} 分钟")
                    st.caption("已运行时间")
            
            st.divider()

def show_completed_tasks(tasks):
    """显示已完成任务"""
    st.subheader("✅ 已完成任务")
    
    if not tasks:
        st.info("📋 暂无已完成任务")
        return
    
    # 按完成时间排序（最新的在前）
    tasks.sort(key=lambda x: x.completed_at or x.created_at, reverse=True)
    
    for task in tasks[:20]:  # 只显示最近20个
        with st.container():
            # 状态颜色
            if task.status == TaskStatus.COMPLETED:
                status_icon = "✅"
                status_color = "green"
            elif task.status == TaskStatus.FAILED:
                status_icon = "❌"
                status_color = "red"
            else:
                status_icon = "⚪"
                status_color = "gray"
            
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            
            with col1:
                st.write(f"**{task.name}**")
                st.caption(f"🏁 完成时间: {format_datetime(task.completed_at)}")
            
            with col2:
                st.write(f"{status_icon} **{task.status.value}**")
                if task.error_message:
                    st.caption(f"错误: {task.error_message[:50]}...")
            
            with col3:
                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    total = task.success_count + task.error_count
                    success_rate = (task.success_count / total * 100) if total > 0 else 0
                    st.write(f"📊 {task.success_count}/{total}")
                    st.caption(f"成功率: {success_rate:.1f}%")
            
            with col4:
                if st.button("🗑️", key=f"delete_{task.id}", help="删除任务"):
                    task_scheduler.delete_task(task.id)
                    st.success("任务已删除")
                    st.rerun()
            
            st.divider()

        # 数据库状态
        st.subheader("💾 数据库状态")
        
        try:
            stats = task_scheduler.get_task_statistics()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("总任务数", stats['total_tasks'])
            with col2:
                st.metric("最近7天", stats['recent_tasks'])
            
            # 状态分布
            if stats['status_counts']:
                st.write("**状态分布:**")
                for status, count in stats['status_counts'].items():
                    st.text(f"{status}: {count}")
            
            # 数据库文件信息
            db_file = Path("data/tasks.db")
            if db_file.exists():
                size_mb = db_file.stat().st_size / 1024 / 1024
                st.caption(f"数据库大小: {size_mb:.2f} MB")
            
        except Exception as e:
            st.error(f"获取数据库状态失败: {e}")
        
        # 数据库管理
        with st.expander("🔧 数据库管理"):
            if st.button("🗑️ 清理30天前任务", use_container_width=True):
                deleted_count = task_scheduler.clean_old_tasks(30)
                if deleted_count > 0:
                    st.success(f"✅ 已清理 {deleted_count} 个旧任务")
                else:
                    st.info("没有需要清理的任务")
                st.rerun()
            
            if st.button("📊 重新统计", use_container_width=True):
                st.rerun()
            
            # 数据备份下载
            try:
                import sqlite3
                import io
                
                if st.button("📥 备份数据库", use_container_width=True):
                    db_file = "data/tasks.db"
                    if os.path.exists(db_file):
                        with open(db_file, 'rb') as f:
                            db_data = f.read()
                        
                        st.download_button(
                            label="⬇️ 下载数据库备份",
                            data=db_data,
                            file_name=f"tasks_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
                            mime="application/octet-stream",
                            use_container_width=True
                        )
            except Exception as e:
                st.error(f"备份功能异常: {e}")
        
        st.markdown("---")
        
        # 快速操作
        st.subheader("🔧 快速操作")
        if st.button("🔄 刷新页面", use_container_width=True):
            st.rerun()
        
        # 清理旧任务
        if st.button("🗑️ 清理旧任务", use_container_width=True):
            clean_old_tasks()
            st.success("旧任务已清理")
            st.rerun()
        
        # 立即创建测试任务
        if st.button("🧪 测试创建", use_container_width=True):
            try:
                test_task = task_scheduler.create_daily_task(5)  # 创建一个5次的测试任务
                st.success(f"✅ 测试任务已创建: {test_task.name}")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 测试创建失败: {e}")
    
    # 主界面 - 任务列表和文件管理
    tasks = task_scheduler.get_tasks()
    
    # 创建标签页
    tab1, tab2, tab3, tab4 = st.tabs([
        f"⏳ 待运行 ({len(tasks['pending'])})",
        f"▶️ 运行中 ({len(tasks['running'])})", 
        f"✅ 已完成 ({len(tasks['completed'])})",
        "📁 文件管理"
    ])
    
    with tab1:
        show_pending_tasks(tasks['pending'])
    
    with tab2:
        show_running_tasks(tasks['running'])
    
    with tab3:
        show_completed_tasks(tasks['completed'])
    
    with tab4:
        show_generated_files()

def show_pending_tasks(tasks):
    """显示待运行任务"""
    st.subheader("⏳ 待运行任务")
    
    if not tasks:
        st.info("📋 暂无待运行任务")
        
        # 显示下次自动创建时间提示
        if task_scheduler.config.auto_create_enabled:
            now = datetime.now()
            tomorrow_create_time = datetime.combine(
                now.date() + timedelta(days=1),
                datetime.strptime(task_scheduler.config.auto_create_time, "%H:%M").time()
            )
            
            # 如果今天的创建时间还没过，则是今天
            today_create_time = datetime.combine(
                now.date(),
                datetime.strptime(task_scheduler.config.auto_create_time, "%H:%M").time()
            )
            
            if now < today_create_time:
                next_create_time = today_create_time
            else:
                next_create_time = tomorrow_create_time
            
            next_execute_time = next_create_time + timedelta(hours=task_scheduler.config.auto_execute_delay_hours)
            
            time_diff = next_execute_time - now
            hours = int(time_diff.total_seconds() // 3600)
            minutes = int((time_diff.total_seconds() % 3600) // 60)
            
            st.info(f"💡 系统将在 {hours}小时{minutes}分钟后执行下一个自动创建的任务")
        else:
            st.warning("⚠️ 自动创建任务已禁用，请手动创建或在侧边栏启用自动创建")
        
        return
    
    for task in tasks:
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            
            with col1:
                # 显示任务类型
                if task.id.startswith('test_'):
                    task_type = "🧪 测试任务"
                else:
                    task_type = "⏰ 定时任务"
                
                st.write(f"**{task_type}**")
                st.write(f"{task.name}")
                st.caption(f"📅 创建时间: {format_datetime(task.created_at)}")
            
            with col2:
                st.write(f"🎯 {task.workflow_count} 次")
                st.caption("执行次数")
            
            with col3:
                # 计算距离执行时间
                now = datetime.now()
                task_created_time = datetime.fromisoformat(task.created_at)
                
                # 根据任务类型计算执行时间
                if task.id.startswith('test_'):
                    task_execute_time = task_created_time + timedelta(minutes=1)
                else:
                    task_execute_time = task_created_time + timedelta(hours=task_scheduler.config.auto_execute_delay_hours)
                
                time_diff = task_execute_time - now
                
                if time_diff.total_seconds() > 0:
                    if task.id.startswith('test_'):
                        # 测试任务显示秒数
                        seconds = int(time_diff.total_seconds())
                        if seconds > 60:
                            minutes = seconds // 60
                            seconds = seconds % 60
                            st.write(f"⏰ {minutes}分{seconds}秒后")
                        else:
                            st.write(f"⏰ {seconds}秒后")
                    else:
                        # 普通任务显示小时分钟
                        hours = int(time_diff.total_seconds() // 3600)
                        minutes = int((time_diff.total_seconds() % 3600) // 60)
                        
                        if hours > 0:
                            st.write(f"⏰ {hours}小时{minutes}分钟后")
                        else:
                            st.write(f"⏰ {minutes}分钟后")
                    
                    st.caption("距离执行时间")
                else:
                    st.write("⏰ 即将执行")
                    st.caption("等待执行中")
            
            with col4:
                # 操作按钮
                col_cancel, col_execute = st.columns(2)
                
                with col_cancel:
                    if st.button("❌", key=f"cancel_{task.id}", help="取消任务"):
                        task_scheduler.cancel_task(task.id)
                        st.success("任务已取消")
                        st.rerun()
                
                with col_execute:
                    # 立即执行按钮（仅对测试任务显示）
                    if task.id.startswith('test_'):
                        if st.button("⚡", key=f"execute_{task.id}", help="立即执行"):
                            task_scheduler.execute_task_immediately(task.id)
                            st.success("任务已开始执行")
                            st.rerun()
            
            st.divider()

def show_running_tasks(tasks):
    """显示运行中任务"""
    st.subheader("▶️ 运行中任务")
    
    if not tasks:
        st.info("📋 暂无运行中任务")
        return
    
    for task in tasks:
        with st.container():
            col1, col2, col3 = st.columns([4, 2, 2])
            
            with col1:
                st.write(f"**{task.name}**")
                st.caption(f"🚀 开始时间: {format_datetime(task.started_at)}")
                
                # 显示进度条（模拟）
                if task.id == task_scheduler.current_task_id:
                    progress_placeholder = st.empty()
                    # 这里可以添加实际进度跟踪
                    with progress_placeholder:
                        st.progress(0.5, "执行中...")
            
            with col2:
                st.write(f"🎯 {task.workflow_count} 次")
                st.caption("目标执行次数")
            
            with col3:
                # 运行时间计算
                if task.started_at:
                    start_time = datetime.fromisoformat(task.started_at)
                    running_time = datetime.now() - start_time
                    minutes = int(running_time.total_seconds() // 60)
                    st.write(f"⏱️ {minutes} 分钟")
                    st.caption("已运行时间")
            
            st.divider()

def show_completed_tasks(tasks):
    """显示已完成任务"""
    st.subheader("✅ 已完成任务")
    
    if not tasks:
        st.info("📋 暂无已完成任务")
        return
    
    # 按完成时间排序（最新的在前）
    tasks.sort(key=lambda x: x.completed_at or x.created_at, reverse=True)
    
    for task in tasks[:20]:  # 只显示最近20个
        with st.container():
            # 状态颜色
            if task.status == TaskStatus.COMPLETED:
                status_icon = "✅"
                status_color = "green"
            elif task.status == TaskStatus.FAILED:
                status_icon = "❌"
                status_color = "red"
            else:
                status_icon = "⚪"
                status_color = "gray"
            
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            
            with col1:
                st.write(f"**{task.name}**")
                st.caption(f"🏁 完成时间: {format_datetime(task.completed_at)}")
            
            with col2:
                st.write(f"{status_icon} **{task.status.value}**")
                if task.error_message:
                    st.caption(f"错误: {task.error_message[:50]}...")
            
            with col3:
                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    total = task.success_count + task.error_count
                    success_rate = (task.success_count / total * 100) if total > 0 else 0
                    st.write(f"📊 {task.success_count}/{total}")
                    st.caption(f"成功率: {success_rate:.1f}%")
            
            with col4:
                if st.button("🗑️", key=f"delete_{task.id}", help="删除任务"):
                    task_scheduler.delete_task(task.id)
                    st.success("任务已删除")
                    st.rerun()
            
            st.divider()

def clean_old_tasks():
    """清理30天前的已完成任务"""
    return task_scheduler.clean_old_tasks(30)

def format_datetime(dt_str):
    """格式化日期时间显示"""
    if not dt_str:
        return "未知"
    
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%m-%d %H:%M")
    except:
        return dt_str

if __name__ == "__main__":
    main()
