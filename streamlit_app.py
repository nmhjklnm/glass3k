import streamlit as st
import asyncio
import time
import os
import tempfile
import zipfile
import io
from datetime import datetime
from typing import List, Dict
import subprocess
import sys
from pathlib import Path
import threading
import queue
import contextlib
from io import StringIO
import json
import uuid  # 新增导入

# 导入现有模块
try:
    from workflow import run_workflow
    from utils import asave_result_to_file
    import marvin
    from pydantic_ai.models.openai import OpenAIModel
    from pydantic_ai.providers.openrouter import OpenRouterProvider
except ImportError as e:
    st.error(f"导入模块失败: {e}")
    st.error("请确保所有依赖都已安装")

class StreamCapture:
    """流式输出捕获器"""
    
    def __init__(self):
        self.output_queue = queue.Queue()
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.capturing = False
    
    def start_capture(self):
        """开始捕获输出"""
        self.capturing = True
        sys.stdout = self
        sys.stderr = self
    
    def stop_capture(self):
        """停止捕获输出"""
        self.capturing = False
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
    
    def write(self, text):
        """写入输出"""
        if self.capturing and text.strip():
            self.output_queue.put(text)
            # 同时输出到原始stdout
            self.original_stdout.write(text)
        return len(text)
    
    def flush(self):
        """刷新缓冲区"""
        self.original_stdout.flush()
    
    def get_output(self):
        """获取所有输出"""
        output = []
        while not self.output_queue.empty():
            try:
                output.append(self.output_queue.get_nowait())
            except queue.Empty:
                break
        return output

class WorkflowRunner:
    """工作流执行器"""
    
    def __init__(self):
        self.results = []
        self.errors = []
        self.stream_capture = StreamCapture()
        self.log_counter = 0  # 新增计数器
        self.setup_model()
    
    def setup_model(self):
        """设置 AI 模型"""
        try:
            # 读取配置文件中的API key
            api_key = self.get_api_key()
            model = OpenAIModel(
                'anthropic/claude-sonnet-4',
                provider=OpenRouterProvider(api_key=api_key),
            )
            marvin.defaults.model = model
        except Exception as e:
            st.error(f"模型设置失败: {e}")
    
    def get_api_key(self):
        """从配置文件读取API key"""
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                    api_key = config.get("api_key")
                    if not api_key:
                        raise ValueError("config.json中未找到api_key")
                    return api_key
            else:
                raise FileNotFoundError("config.json文件不存在")
        except Exception as e:
            st.error(f"读取API key失败: {e}")
            st.error("请在config.json中配置有效的api_key")
            return None
    
    def save_api_key(self, api_key):
        """保存API key到配置文件"""
        try:
            config = {"api_key": api_key}
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            st.error(f"保存API key失败: {e}")
            return False

    async def run_single_workflow(self, index: int = 0) -> Dict:
        """执行单次工作流"""
        try:
            print(f"🚀 开始执行第 {index + 1} 次工作流...")
            result = await run_workflow()
            print(f"✅ 工作流执行成功，开始保存结果...")
            saved_file = await asave_result_to_file(result)
            print(f"📁 结果已保存到: {saved_file}")
            
            return {
                'success': True,
                'result': result,
                'saved_file': saved_file,
                'error': None
            }
        except Exception as e:
            error_msg = str(e)
            print(f"❌ 第 {index + 1} 次执行失败: {error_msg}")
            return {
                'success': False,
                'result': None,
                'saved_file': None,
                'error': error_msg
            }
    
    async def run_batch_workflows(self, count: int, progress_callback=None, log_callback=None):
        """批量执行工作流"""
        self.results = []
        self.errors = []
        
        # 开始捕获输出
        self.stream_capture.start_capture()
        
        try:
            for i in range(count):
                if progress_callback:
                    progress_callback(i, count)
                
                print(f"\n{'='*50}")
                print(f"📊 执行进度: {i+1}/{count}")
                print(f"{'='*50}")
                
                result = await self.run_single_workflow(i)
                
                if result['success']:
                    self.results.append(result)
                    print(f"🎉 第 {i+1} 次执行成功完成！")
                else:
                    self.errors.append({
                        'index': i + 1,
                        'error': result['error']
                    })
                    print(f"💥 第 {i+1} 次执行失败！")
                
                # 获取并传递日志
                if log_callback:
                    logs = self.stream_capture.get_output()
                    if logs:
                        log_callback(logs)
                
                # 添加小延迟避免过快请求
                print(f"⏳ 等待 0.5 秒后继续...")
                await asyncio.sleep(0.5)
            
            if progress_callback:
                progress_callback(count, count)
                
        finally:
            # 停止捕获输出
            self.stream_capture.stop_capture()

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

def show_api_config():
    """显示API配置面板"""
    st.subheader("🔑 API 配置")
    
    runner = WorkflowRunner()
    
    # 显示当前API key（部分隐藏）
    current_key = runner.get_api_key()
    masked_key = f"{current_key[:10]}...{current_key[-4:]}" if len(current_key) > 14 else "***"
    st.text(f"当前API Key: {masked_key}")
    
    # API key修改表单
    with st.form("api_config_form"):
        new_api_key = st.text_input(
            "新的 API Key",
            value=current_key,
            type="password",
            help="请输入有效的 OpenRouter API Key"
        )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.form_submit_button("💾 保存", type="primary"):
                if not new_api_key.strip():
                    st.error("❌ API Key 不能为空")
                else:
                    if runner.save_api_key(new_api_key.strip()):
                        st.success("✅ API Key 保存成功！")
                        st.info("ℹ️ 新配置将在下次执行工作流时生效")
                        st.rerun()
        
        with col2:
            if st.form_submit_button("🔍 测试"):
                test_api_key(new_api_key.strip())
        
        with col3:
            if st.form_submit_button("🔄 重置"):
                default_key = "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"
                if runner.save_api_key(default_key):
                    st.success("✅ 已重置为默认 API Key")
                    st.rerun()

def test_api_key(api_key: str):
    """测试API key连接"""
    if not api_key:
        st.error("❌ 请先输入API Key")
        return
    
    with st.spinner("🔍 测试API连接..."):
        try:
            test_model = OpenAIModel(
                'anthropic/claude-sonnet-4',
                provider=OpenRouterProvider(api_key=api_key),
            )
            
            import marvin
            old_model = marvin.defaults.model
            marvin.defaults.model = test_model
            
            # 执行简单测试
            test_result = marvin.generate(
                str,
                instructions="请回复'连接成功'",
                n=1
            )
            
            # 恢复原模型
            marvin.defaults.model = old_model
            
            if test_result:
                st.success("✅ API连接测试成功！")
            else:
                st.warning("⚠️ API连接成功，但返回结果为空")
                
        except Exception as e:
            st.error(f"❌ API连接测试失败: {str(e)}")

def main():
    """主应用界面"""
    st.set_page_config(
        page_title="Glass3K Workflow 执行器",
        page_icon="👓",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 标题和描述
    st.title("👓 Glass3K Workflow 执行器")
    
    # 添加页面导航提示
    st.info("💡 **新功能**: 访问侧边栏中的 **📅 任务管理** 页面来设置定时任务！")
    
    st.markdown("---")
    
    # 侧边栏配置
    with st.sidebar:
        st.header("⚙️ 执行配置")
        
        # 执行次数选择
        execution_count = st.number_input(
            "执行次数",
            min_value=1,
            max_value=100,
            value=5,
            help="选择要执行 workflow.py 的次数"
        )
        
        # 高级选项
        with st.expander("🔧 高级选项"):
            show_detailed_logs = st.checkbox("显示详细日志", value=True)
            show_realtime_output = st.checkbox("显示实时输出", value=True)
            auto_refresh = st.checkbox("自动刷新状态", value=True)
        
        st.markdown("---")
        
        # API配置区域
        show_api_config()
        
        st.markdown("---")
        
        # 文件管理区域
        st.subheader("📁 文件管理")
        
        # 刷新按钮
        col_refresh, col_spacer = st.columns([1, 2])
        with col_refresh:
            if st.button("🔄 刷新", use_container_width=True, help="刷新文件列表和统计信息"):
                st.rerun()
        
        # 统计信息
        data_dir = Path("data")
        file_count = 0
        total_size = 0
        
        if data_dir.exists():
            files = list(data_dir.glob("result_*.txt"))
            file_count = len(files)
            total_size = sum(f.stat().st_size for f in files)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("文件数量", file_count)
        with col2:
            st.metric("总大小", f"{total_size / 1024:.1f} KB")
        
        # 文件操作按钮
        if file_count > 0:
            zip_data = create_download_zip()
            if zip_data:
                st.download_button(
                    label="📦 下载所有文件",
                    data=zip_data,
                    file_name=f"glass3k_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    mime="application/zip",
                    use_container_width=True
                )
            
            # 删除按钮
            if st.button("🗑️ 删除所有文件", use_container_width=True, type="secondary"):
                deleted_count = delete_all_txt_files()
                if deleted_count > 0:
                    st.success(f"✅ 已删除 {deleted_count} 个文件")
                    st.rerun()
                else:
                    st.info("没有文件需要删除")
        else:
            st.info("暂无文件可管理")
        
        st.markdown("---")
        
        # 环境信息
        st.subheader("📋 环境信息")
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        st.text(f"Python: {python_version}")
        
        # 检查关键文件
        workflow_exists = os.path.exists("workflow.py")
        config_exists = os.path.exists("config.json")
        st.text(f"workflow.py: {'✅' if workflow_exists else '❌'}")
        st.text(f"config.json: {'✅' if config_exists else '⚠️'}")
        
        # 虚拟环境检查
        venv_active = os.environ.get('VIRTUAL_ENV') is not None
        st.text(f"虚拟环境: {'✅' if venv_active else '⚠️'}")
    
    # 主界面
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🚀 执行控制")
        
        # 执行按钮
        if st.button(
            f"开始执行 ({execution_count} 次)",
            type="primary",
            use_container_width=True
        ):
            if not workflow_exists:
                st.error("❌ workflow.py 文件不存在！")
                return
            
            # 执行工作流
            run_workflows(execution_count, show_detailed_logs, show_realtime_output)
    
    with col2:
        st.subheader("📊 快速统计")
        
        # 检查数据目录
        data_dir = Path("data")
        if data_dir.exists():
            files = list(data_dir.glob("result_*.txt"))
            st.metric("已生成文件", len(files))
            
            if files:
                latest_file = max(files, key=os.path.getctime)
                latest_time = datetime.fromtimestamp(
                    os.path.getctime(latest_file)
                ).strftime("%H:%M:%S")
                st.metric("最新生成", latest_time)
        else:
            st.metric("已生成文件", "0")
    
    # 历史记录和日志
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["📈 执行历史", "📋 生成文件", "🔍 错误日志"])
    
    with tab1:
        show_execution_history()
    
    with tab2:
        show_generated_files()
    
    with tab3:
        show_error_logs()

def run_workflows(count: int, show_logs: bool = True, show_realtime: bool = True):
    """执行工作流的主函数"""
    runner = WorkflowRunner()
    
    # 创建状态容器
    status_container = st.container()
    progress_container = st.container()
    
    # 实时输出容器
    if show_realtime:
        realtime_container = st.container()
        with realtime_container:
            st.subheader("📺 实时输出")
            log_placeholder = st.empty()
            log_content = []
    
    results_container = st.container()
    
    with status_container:
        st.info(f"🔄 准备执行 {count} 次工作流...")
    
    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()
    
    # 执行统计
    start_time = time.time()
    success_count = 0
    error_count = 0
    
    def update_progress(current: int, total: int):
        progress = current / total
        progress_bar.progress(progress)
        status_text.text(f"执行进度: {current}/{total} ({progress:.1%})")
    
    def update_logs(new_logs):
        """更新实时日志显示"""
        if show_realtime:
            log_content.extend(new_logs)
            # 只保留最近的50条日志
            if len(log_content) > 50:
                log_content[:] = log_content[-50:]
            
            # 格式化并显示日志
            formatted_logs = []
            for log in log_content[-20:]:  # 只显示最近20条
                if log.strip():
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    formatted_logs.append(f"[{timestamp}] {log.strip()}")
            
            if formatted_logs:
                log_text = "\n".join(formatted_logs)
                # 使用唯一的key生成策略
                runner.log_counter += 1
                unique_key = f"log_{int(time.time())}_{runner.log_counter}_{uuid.uuid4().hex[:8]}"
                log_placeholder.text_area(
                    "实时日志",
                    value=log_text,
                    height=300,
                    key=unique_key
                )
    
    # 异步执行
    async def run_async():
        nonlocal success_count, error_count
        await runner.run_batch_workflows(count, update_progress, update_logs)
        success_count = len(runner.results)
        error_count = len(runner.errors)
    
    # 运行异步任务
    try:
        asyncio.run(run_async())
    except Exception as e:
        st.error(f"执行过程中发生错误: {e}")
        return
    
    # 计算执行时间
    execution_time = time.time() - start_time
    
    # 显示结果
    with results_container:
        st.success("✅ 执行完成！")
        
        # 统计信息
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总执行次数", count)
        with col2:
            st.metric("成功次数", success_count)
        with col3:
            st.metric("失败次数", error_count)
        with col4:
            success_rate = (success_count / count) * 100 if count > 0 else 0
            st.metric("成功率", f"{success_rate:.1f}%")
        
        st.text(f"⏱️ 总耗时: {execution_time:.2f} 秒")
        
        # 显示详细结果
        if show_logs and runner.results:
            with st.expander("📋 成功执行详情", expanded=False):
                for i, result in enumerate(runner.results[:5]):  # 只显示前5个
                    content = result['result'].generated_content
                    st.write(f"**第 {i+1} 次执行**")
                    st.write(f"- 标题: {content.title}")
                    st.write(f"- 保存文件: {result['saved_file']}")
                    st.write("---")
        
        # 显示错误信息
        if runner.errors:
            with st.expander("❌ 执行错误详情", expanded=True):
                for error in runner.errors:
                    st.error(f"第 {error['index']} 次执行失败: {error['error']}")
        
        # 保存执行历史到session state
        if 'execution_history' not in st.session_state:
            st.session_state.execution_history = []
        
        st.session_state.execution_history.append({
            'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'count': count,
            'success': success_count,
            'error': error_count,
            'success_rate': f"{success_rate:.1f}%",
            'duration': f"{execution_time:.2f}s"
        })

def show_execution_history():
    """显示执行历史"""
    st.subheader("📈 执行历史记录")
    
    if st.session_state.get('execution_history'):
        history = st.session_state.execution_history[-10:]  # 显示最近10条
        
        for i, record in enumerate(reversed(history)):
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
                with col1:
                    st.text(f"⏰ {record['time']}")
                with col2:
                    st.text(f"📊 {record['count']} 次")
                with col3:
                    st.text(f"✅ {record['success']}")
                with col4:
                    st.text(f"❌ {record['error']}")
                with col5:
                    st.text(f"📈 {record['success_rate']}")
                
                if i < len(history) - 1:
                    st.divider()
        
        # 清空历史按钮
        if st.button("🗑️ 清空执行历史"):
            st.session_state.execution_history = []
            st.success("执行历史已清空")
            st.rerun()
    else:
        st.info("暂无执行历史记录")

def show_generated_files():
    """显示生成的文件"""
    col_title, col_refresh = st.columns([3, 1])
    
    with col_title:
        st.subheader("📋 生成文件列表")
    
    with col_refresh:
        if st.button("🔄 刷新文件列表", help="重新加载文件列表"):
            st.rerun()
    
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
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("文件总数", total_files)
    with col2:
        st.metric("总大小", f"{total_size_bytes / 1024:.1f} KB")
    with col3:
        if files:
            latest_file = max(files, key=os.path.getctime)
            latest_time = datetime.fromtimestamp(os.path.getctime(latest_file))
            st.metric("最新文件", latest_time.strftime("%H:%M:%S"))
    
    st.markdown("---")
    
    # 文件列表
    for file in files[:20]:  # 显示最近20个文件
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
                if st.button("👁️", key=f"preview_{file.name}", help="预览文件"):
                    try:
                        with open(file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        st.text_area("文件内容预览", content, height=200, key=f"content_{file.name}")
                    except Exception as e:
                        st.error(f"读取文件失败: {e}")
            with col5:
                # 删除单个文件按钮
                if st.button("🗑️", key=f"delete_{file.name}", help="删除此文件"):
                    try:
                        file.unlink()
                        st.success(f"✅ 已删除 {file.name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"删除文件失败: {e}")

def show_error_logs():
    """显示错误日志"""
    st.subheader("🔍 错误日志")
    
    error_log_file = "workflow_errors.log"
    if not os.path.exists(error_log_file):
        st.info("暂无错误日志")
        return
    
    try:
        with open(error_log_file, 'r', encoding='utf-8') as f:
            error_content = f.read()
        
        if error_content.strip():
            st.text_area("错误日志内容", error_content, height=300)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ 清空错误日志"):
                    with open(error_log_file, 'w') as f:
                        f.write("")
                    st.success("错误日志已清空")
                    st.rerun()
            
            with col2:
                # 下载错误日志
                st.download_button(
                    label="📥 下载错误日志",
                    data=error_content,
                    file_name=f"error_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
                    mime="text/plain"
                )
        else:
            st.info("错误日志为空")
    
    except Exception as e:
        st.error(f"读取错误日志失败: {e}")

if __name__ == "__main__":
    main()
