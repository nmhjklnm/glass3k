#!/bin/bash
# filepath: /Users/apple/Desktop/project/glass3k/run_workflow.sh

# 注释掉全局错误退出设置，改为局部控制
# set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 错误日志文件
ERROR_LOG="workflow_errors.log"

# 打印带颜色的消息
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# 检查Python环境
check_python_env() {
    if [ ! -d "./venv" ] && [ ! -d "./.venv" ] && [ -z "$VIRTUAL_ENV" ]; then
        print_message $YELLOW "警告: 未找到虚拟环境目录 (venv 或 .venv)，且当前未激活虚拟环境"
        read -p "是否继续执行? (y/N): " continue_choice
        if [[ ! $continue_choice =~ ^[Yy]$ ]]; then
            print_message $RED "脚本已取消"
            exit 1
        fi
    fi
}

# 激活Python虚拟环境
activate_env() {
    if [ -n "$VIRTUAL_ENV" ]; then
        print_message $GREEN "✅ 虚拟环境已激活: $VIRTUAL_ENV"
    elif [ -d "./venv" ]; then
        print_message $BLUE "🔄 激活虚拟环境: venv"
         
        print_message $GREEN "✅ 虚拟环境已激活"
    elif [ -d "./.venv" ]; then
        print_message $BLUE "🔄 激活虚拟环境: .venv"
        source ./.venv/bin/activate
        print_message $GREEN "✅ 虚拟环境已激活"
    else
        print_message $YELLOW "⚠️  未找到虚拟环境，使用系统Python环境"
    fi
}

# 检查workflow.py文件
check_workflow_file() {
    if [ ! -f "./workflow.py" ]; then
        print_message $RED "❌ 错误: workflow.py 文件不存在"
        exit 1
    fi
}

# 询问用户执行次数
get_execution_count() {
    while true; do
        read -p "请输入需要执行workflow.py的次数 (1-100): " count
        
        # 检查输入是否为数字
        if ! [[ "$count" =~ ^[0-9]+$ ]]; then
            print_message $RED "❌ 请输入有效的数字"
            continue
        fi
        
        # 检查数字范围
        if [ "$count" -lt 1 ] || [ "$count" -gt 100 ]; then
            print_message $RED "❌ 请输入1到100之间的数字"
            continue
        fi
        
        break
    done
    
    echo $count
}

# 用户确认
confirm_execution() {
    local count=$1
    print_message $YELLOW "📋 执行计划:"
    echo "   - 执行次数: $count"
    echo "   - 脚本文件: workflow.py"
    echo ""
    
    read -p "确认执行? (y/N): " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        print_message $RED "❌ 用户取消执行"
        exit 1
    fi
}

# 执行workflow.py
run_workflow() {
    local count=$1
    local success_count=0
    local fail_count=0
    local error_details=()
    
    print_message $GREEN "🚀 开始执行workflow.py，共 $count 次"
    echo ""
    
    # 清空或创建错误日志文件
    > "$ERROR_LOG"
    
    for ((i=1; i<=count; i++)); do
        print_message $BLUE "📈 执行第 $i/$count 次..."
        
        # 使用临时文件捕获错误输出
        local temp_error_file=$(mktemp)
        
        # 执行workflow.py，捕获所有输出和错误
        if python workflow.py 2>"$temp_error_file"; then
            ((success_count++))
            print_message $GREEN "✅ 第 $i 次执行成功"
        else
            ((fail_count++))
            local error_msg=$(cat "$temp_error_file")
            print_message $RED "❌ 第 $i 次执行失败"
            
            # 记录错误详情
            echo "=== 执行 #$i 失败 ($(date)) ===" >> "$ERROR_LOG"
            echo "$error_msg" >> "$ERROR_LOG"
            echo "" >> "$ERROR_LOG"
            
            # 保存错误摘要用于最终报告
            local error_summary=$(echo "$error_msg" | head -n 3 | tr '\n' ' ')
            error_details+=("第${i}次: ${error_summary}")
            
            print_message $YELLOW "⚠️  错误详情已记录到 $ERROR_LOG"
        fi
        
        # 清理临时文件
        rm -f "$temp_error_file"
        
        echo "----------------------------------------"
        
        # 如果不是最后一次执行，稍作延迟
        if [ $i -lt $count ]; then
            sleep 1
        fi
    done
    
    # 执行总结
    print_message $GREEN "📊 执行完成!"
    echo "   ✅ 成功: $success_count 次"
    echo "   ❌ 失败: $fail_count 次"
    echo "   📝 总计: $count 次"
    
    # 如果有失败的执行，显示详细信息
    if [ $fail_count -gt 0 ]; then
        echo ""
        print_message $YELLOW "❌ 失败详情:"
        for error in "${error_details[@]}"; do
            echo "   $error"
        done
        echo ""
        print_message $BLUE "📋 完整错误日志请查看: $ERROR_LOG"
    fi
    
    # 计算成功率
    local success_rate=$((success_count * 100 / count))
    if [ $success_rate -eq 100 ]; then
        print_message $GREEN "🎯 成功率: 100% - 完美执行!"
    elif [ $success_rate -ge 80 ]; then
        print_message $YELLOW "🎯 成功率: ${success_rate}% - 表现良好"
    else
        print_message $RED "🎯 成功率: ${success_rate}% - 需要关注"
    fi
}

# 主函数
main() {
    print_message $BLUE "🔧 Glass3K Workflow 批量执行工具"
    echo ""
    
    # 检查Python环境
    check_python_env
    
    # 激活虚拟环境
    activate_env
    
    # 检查workflow.py文件
    check_workflow_file
    
    # 获取执行次数
    execution_count=$(get_execution_count)
    
    # 用户确认
    confirm_execution $execution_count
    
    # 执行workflow
    run_workflow $execution_count
    
    print_message $GREEN "🎉 所有任务完成!"
}

# 脚本入口
main "$@"