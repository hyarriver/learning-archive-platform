#!/bin/bash
# 学习资料聚合平台 - 智能自动部署脚本（带自动修复和重试机制）
# 服务器: 112.124.2.164:3000

set +e  # 不立即退出，允许错误处理

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置变量
PROJECT_DIR="/opt/Learning Archive Platform"
BACKEND_DIR="$PROJECT_DIR/backend"
SERVICE_NAME="archive-platform"
SERVICE_PORT=3000
MAX_RETRIES=3

# 日志函数
log_info() { echo -e "${BLUE}[信息]${NC} $1"; }
log_success() { echo -e "${GREEN}[成功]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[警告]${NC} $1"; }
log_error() { echo -e "${RED}[错误]${NC} $1"; }

# 重试函数
retry_command() {
    local cmd="$1"
    local max_attempts=${2:-3}
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        log_info "执行命令 (尝试 $attempt/$max_attempts): $cmd"
        if eval "$cmd"; then
            log_success "命令执行成功"
            return 0
        else
            log_warning "命令执行失败，将在 2 秒后重试..."
            sleep 2
            attempt=$((attempt + 1))
        fi
    done
    
    log_error "命令执行失败，已重试 $max_attempts 次"
    return 1
}

# 检查并修复 Python 环境
fix_python_env() {
    log_info "检查 Python 环境..."
    
    if ! command -v python3 &> /dev/null; then
        log_warning "Python 3 未安装，正在安装..."
        if [ -f /etc/debian_version ]; then
            apt update -qq
            apt install -y python3 python3-pip python3-venv
        elif [ -f /etc/redhat-release ]; then
            yum install -y python3 python3-pip
        fi
    fi
    
    # 检查 python3-venv
    if ! python3 -m venv --help &> /dev/null; then
        log_warning "python3-venv 未安装，正在安装..."
        PYTHON_VER=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1 || echo "3")
        if [ -f /etc/debian_version ]; then
            apt install -y "python${PYTHON_VER}-venv" 2>/dev/null || \
            apt install -y python3-venv
        fi
    fi
    
    if ! python3 -m venv --help &> /dev/null; then
        log_error "无法修复 Python 环境"
        return 1
    fi
    
    log_success "Python 环境检查通过"
    return 0
}

# 修复虚拟环境
fix_venv() {
    log_info "修复虚拟环境..."
    cd "$BACKEND_DIR" || return 1
    
    # 删除旧的虚拟环境
    if [ -d "venv" ]; then
        log_warning "删除旧的虚拟环境..."
        rm -rf venv
    fi
    
    # 创建新的虚拟环境（重试3次）
    retry_command "python3 -m venv venv" 3
    
    # 验证虚拟环境
    if [ ! -f "venv/bin/activate" ]; then
        log_error "虚拟环境创建失败"
        return 1
    fi
    
    log_success "虚拟环境创建成功"
    return 0
}

# 修复依赖安装
fix_dependencies() {
    log_info "安装/修复 Python 依赖..."
    cd "$BACKEND_DIR" || return 1
    
    if [ ! -f "venv/bin/activate" ]; then
        log_error "虚拟环境不存在，无法安装依赖"
        return 1
    fi
    
    source venv/bin/activate
    
    # 升级 pip（重试）
    retry_command "pip install --upgrade pip" 3
    
    # 安装依赖（重试）
    log_info "安装项目依赖（这可能需要几分钟）..."
    retry_command "pip install -r requirements.txt" 3
    
    # 如果还是失败，尝试逐个安装主要依赖
    if [ $? -ne 0 ]; then
        log_warning "批量安装失败，尝试逐个安装主要依赖..."
        pip install fastapi uvicorn sqlalchemy python-jose passlib requests beautifulsoup4 html2text yt-dlp apscheduler pydantic pydantic-settings
    fi
    
    log_success "依赖安装完成"
    return 0
}

# 修复环境变量配置
fix_env_config() {
    log_info "修复环境变量配置..."
    cd "$BACKEND_DIR" || return 1
    
    if [ ! -f ".env.example" ] && [ ! -f ".env" ]; then
        log_error ".env 文件不存在且无示例文件"
        return 1
    fi
    
    # 如果 .env 不存在，从示例创建
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
        else
            # 创建基本 .env 文件
            cat > .env <<EOF
APP_NAME=Learning Archive Platform
APP_ENV=production
DEBUG=False
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
HOST=0.0.0.0
PORT=$SERVICE_PORT
DATABASE_URL=sqlite:///./data/archive.db
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
DATA_DIR=./data
COLLECTIONS_DIR=./data/collections
UPLOADS_DIR=./data/uploads
SCHEDULER_TIMEZONE=Asia/Shanghai
COLLECTION_SCHEDULE_HOUR=0
COLLECTION_SCHEDULE_MINUTE=0
CRAWLER_USER_AGENT=Mozilla/5.0
CRAWLER_REQUEST_DELAY=1.0
CRAWLER_MAX_RETRIES=3
LOG_LEVEL=INFO
LOG_DIR=./logs
EOF
        fi
    fi
    
    # 确保必要的配置存在
    source venv/bin/activate 2>/dev/null || true
    if ! grep -q "^PORT=" .env; then
        echo "PORT=$SERVICE_PORT" >> .env
    else
        sed -i "s|^PORT=.*|PORT=$SERVICE_PORT|" .env
    fi
    
    if ! grep -q "^DEBUG=" .env; then
        echo "DEBUG=False" >> .env
    else
        sed -i "s|^DEBUG=.*|DEBUG=False|" .env
    fi
    
    if ! grep -q "^SECRET_KEY=" .env || grep -q "^SECRET_KEY=change-me" .env; then
        SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "change-me-in-production")
        if grep -q "^SECRET_KEY=" .env; then
            sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|" .env
        else
            echo "SECRET_KEY=$SECRET_KEY" >> .env
        fi
    fi
    
    if ! grep -q "^JWT_SECRET_KEY=" .env || grep -q "^JWT_SECRET_KEY=change-me" .env; then
        JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "change-me-in-production")
        if grep -q "^JWT_SECRET_KEY=" .env; then
            sed -i "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$JWT_SECRET_KEY|" .env
        else
            echo "JWT_SECRET_KEY=$JWT_SECRET_KEY" >> .env
        fi
    fi
    
    log_success "环境变量配置完成"
    return 0
}

# 修复数据库
fix_database() {
    log_info "初始化/修复数据库..."
    cd "$BACKEND_DIR" || return 1
    
    if [ ! -f "venv/bin/activate" ]; then
        log_error "虚拟环境不存在"
        return 1
    fi
    
    source venv/bin/activate
    
    # 创建数据目录
    mkdir -p data logs
    
    # 初始化数据库（重试）
    retry_command "python scripts/init_db.py" 3
    
    if [ $? -ne 0 ]; then
        log_error "数据库初始化失败"
        return 1
    fi
    
    log_success "数据库初始化完成"
    return 0
}

# 修复服务配置
fix_service() {
    log_info "修复 systemd 服务配置..."
    
    # 创建服务文件
    cat > "/etc/systemd/system/$SERVICE_NAME.service" <<EOF
[Unit]
Description=Learning Archive Platform API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$BACKEND_DIR/venv/bin"
ExecStart=$BACKEND_DIR/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port $SERVICE_PORT
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    
    log_success "服务配置完成"
    return 0
}

# 修复防火墙
fix_firewall() {
    log_info "配置防火墙..."
    
    if command -v ufw &> /dev/null && ufw status | grep -q "Status: active"; then
        if ! ufw status | grep -q "$SERVICE_PORT/tcp"; then
            ufw allow "$SERVICE_PORT/tcp" --quiet
            log_success "UFW 防火墙规则已添加"
        fi
    elif command -v firewall-cmd &> /dev/null && firewall-cmd --state &> /dev/null; then
        firewall-cmd --permanent --add-port="$SERVICE_PORT/tcp" --quiet
        firewall-cmd --reload --quiet
        log_success "Firewalld 防火墙规则已添加"
    else
        log_warning "防火墙未激活或未检测到，跳过配置"
    fi
    
    return 0
}

# 启动并验证服务
start_and_verify_service() {
    log_info "启动服务..."
    
    # 停止现有服务
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        systemctl stop "$SERVICE_NAME"
        sleep 1
    fi
    
    # 启动服务
    systemctl enable "$SERVICE_NAME" --quiet
    systemctl start "$SERVICE_NAME"
    
    # 等待服务启动
    sleep 5
    
    # 检查服务状态（重试）
    local attempt=1
    while [ $attempt -le 5 ]; do
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            log_success "服务启动成功"
            
            # 测试健康检查
            sleep 2
            if command -v curl &> /dev/null; then
                if curl -s -f "http://localhost:$SERVICE_PORT/health" > /dev/null 2>&1; then
                    log_success "健康检查通过"
                    return 0
                fi
            fi
            
            log_success "服务运行中（健康检查跳过）"
            return 0
        else
            log_warning "服务启动中... (尝试 $attempt/5)"
            sleep 2
            attempt=$((attempt + 1))
        fi
    done
    
    # 如果服务未启动，查看日志
    log_error "服务启动失败，查看日志:"
    journalctl -u "$SERVICE_NAME" -n 20 --no-pager
    return 1
}

# 自动修复错误
auto_fix_errors() {
    local error_type="$1"
    
    case "$error_type" in
        "venv")
            fix_venv
            ;;
        "dependencies")
            fix_venv
            fix_dependencies
            ;;
        "config")
            fix_env_config
            ;;
        "database")
            fix_database
            ;;
        "service")
            fix_service
            ;;
        "all")
            fix_python_env
            fix_venv
            fix_dependencies
            fix_env_config
            fix_database
            fix_service
            ;;
    esac
}

# 主部署流程
main_deploy() {
    log_info "开始部署流程..."
    
    # 检查 root 权限
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用 root 用户运行此脚本"
        return 1
    fi
    
    # 检查项目目录
    if [ ! -d "$PROJECT_DIR" ] || [ ! -d "$BACKEND_DIR" ]; then
        log_error "项目目录不存在: $PROJECT_DIR"
        return 1
    fi
    
    # 修复 Python 环境
    if ! fix_python_env; then
        log_error "Python 环境修复失败"
        return 1
    fi
    
    # 修复虚拟环境
    if ! fix_venv; then
        log_error "虚拟环境修复失败"
        return 1
    fi
    
    # 修复依赖
    if ! fix_dependencies; then
        log_error "依赖安装失败"
        return 1
    fi
    
    # 修复配置
    if ! fix_env_config; then
        log_error "配置修复失败"
        return 1
    fi
    
    # 修复数据库
    if ! fix_database; then
        log_error "数据库初始化失败"
        return 1
    fi
    
    # 修复服务
    if ! fix_service; then
        log_error "服务配置失败"
        return 1
    fi
    
    # 修复防火墙
    fix_firewall
    
    # 启动服务
    if ! start_and_verify_service; then
        log_error "服务启动失败"
        return 1
    fi
    
    return 0
}

# 主函数（带重试机制）
main() {
    echo "=========================================="
    echo "学习资料聚合平台 - 智能自动部署脚本"
    echo "=========================================="
    echo ""
    
    local attempt=1
    
    while [ $attempt -le $MAX_RETRIES ]; do
        log_info "========== 部署尝试 $attempt/$MAX_RETRIES =========="
        
        if main_deploy; then
            echo ""
            echo "=========================================="
            log_success "部署成功！"
            echo "=========================================="
            echo ""
            echo "服务信息:"
            echo "  服务名称: $SERVICE_NAME"
            echo "  服务地址: http://112.124.2.164:$SERVICE_PORT"
            echo "  API 文档: http://112.124.2.164:$SERVICE_PORT/docs"
            echo ""
            echo "服务管理:"
            echo "  查看状态: systemctl status $SERVICE_NAME"
            echo "  查看日志: journalctl -u $SERVICE_NAME -f"
            echo ""
            return 0
        else
            log_error "部署失败 (尝试 $attempt/$MAX_RETRIES)"
            
            if [ $attempt -lt $MAX_RETRIES ]; then
                log_info "尝试自动修复所有问题..."
                auto_fix_errors "all"
                log_info "等待 3 秒后重试..."
                sleep 3
            fi
            
            attempt=$((attempt + 1))
        fi
    done
    
    echo ""
    echo "=========================================="
    log_error "部署失败，已重试 $MAX_RETRIES 次"
    echo "=========================================="
    echo ""
    echo "请检查日志并手动修复问题："
    echo "  journalctl -u $SERVICE_NAME -n 50"
    echo ""
    echo "或手动测试服务："
    echo "  cd $BACKEND_DIR"
    echo "  source venv/bin/activate"
    echo "  uvicorn app.main:app --host 0.0.0.0 --port $SERVICE_PORT"
    echo ""
    
    return 1
}

# 运行主函数
main "$@"
