#!/bin/bash
# 学习资料聚合平台 - 完整自动部署脚本
# 服务器: 112.124.2.164:3000

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
PROJECT_DIR="/opt/Learning Archive Platform"
BACKEND_DIR="$PROJECT_DIR/backend"
SERVICE_NAME="archive-platform"
SERVICE_PORT=3000

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[信息]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[成功]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[警告]${NC} $1"
}

print_error() {
    echo -e "${RED}[错误]${NC} $1"
}

# 检查是否为 root 用户
check_root() {
    if [ "$EUID" -ne 0 ]; then 
        print_error "请使用 root 用户运行此脚本"
        exit 1
    fi
}

# 检查 Python 环境
check_python() {
    print_info "检查 Python 环境..."
    
    if ! command -v python3 &> /dev/null; then
        print_warning "Python 3 未安装，正在安装..."
        if [ -f /etc/debian_version ]; then
            apt update
            apt install -y python3 python3-pip python3-venv
        elif [ -f /etc/redhat-release ]; then
            yum install -y python3 python3-pip
        else
            print_error "无法检测系统类型，请手动安装 Python 3"
            exit 1
        fi
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    print_success "Python 版本: $(python3 --version)"
    
    # 检查 python3-venv
    if ! python3 -m venv --help &> /dev/null; then
        print_warning "python3-venv 未安装，正在安装..."
        if [ -f /etc/debian_version ]; then
            PYTHON_VER=$(python3 --version | grep -oP '\d+\.\d+' | head -1)
            apt install -y "python${PYTHON_VER}-venv" || apt install -y python3-venv
        fi
    fi
}

# 检查项目目录
check_project_dir() {
    print_info "检查项目目录..."
    
    if [ ! -d "$PROJECT_DIR" ]; then
        print_error "项目目录不存在: $PROJECT_DIR"
        print_info "请先上传项目文件到服务器"
        exit 1
    fi
    
    if [ ! -d "$BACKEND_DIR" ]; then
        print_error "后端目录不存在: $BACKEND_DIR"
        exit 1
    fi
    
    print_success "项目目录检查通过"
}

# 创建虚拟环境
setup_venv() {
    print_info "设置 Python 虚拟环境..."
    cd "$BACKEND_DIR"
    
    # 删除旧的虚拟环境（如果存在）
    if [ -d "venv" ]; then
        print_warning "删除旧的虚拟环境..."
        rm -rf venv
    fi
    
    # 创建新的虚拟环境
    print_info "创建新的虚拟环境..."
    if ! python3 -m venv venv; then
        print_error "虚拟环境创建失败！"
        print_info "尝试安装 python3-venv..."
        PYTHON_VER=$(python3 --version | grep -oP '\d+\.\d+' | head -1)
        if [ -f /etc/debian_version ]; then
            apt install -y "python${PYTHON_VER}-venv" || apt install -y python3-venv
            python3 -m venv venv
        else
            exit 1
        fi
    fi
    
    # 验证虚拟环境
    if [ ! -f "venv/bin/activate" ]; then
        print_error "虚拟环境创建失败，激活文件不存在"
        exit 1
    fi
    
    print_success "虚拟环境创建成功"
}

# 安装 Python 依赖
install_dependencies() {
    print_info "安装 Python 依赖..."
    cd "$BACKEND_DIR"
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 升级 pip
    print_info "升级 pip..."
    pip install --upgrade pip -q
    
    # 安装依赖
    print_info "安装项目依赖（这可能需要几分钟）..."
    if ! pip install -r requirements.txt -q; then
        print_warning "部分依赖安装失败，尝试详细安装..."
        pip install -r requirements.txt
    fi
    
    print_success "依赖安装完成"
}

# 配置环境变量
setup_env() {
    print_info "配置环境变量..."
    cd "$BACKEND_DIR"
    
    if [ -f ".env" ]; then
        print_warning ".env 文件已存在，是否覆盖？(y/n)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            print_info "保留现有 .env 文件"
            return
        fi
    fi
    
    # 复制示例文件
    if [ ! -f ".env.example" ]; then
        print_error ".env.example 文件不存在"
        exit 1
    fi
    
    cp .env.example .env
    
    # 生成随机密钥
    print_info "生成随机密钥..."
    source venv/bin/activate
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    
    # 更新 .env 文件
    print_info "更新 .env 配置..."
    sed -i "s|^PORT=.*|PORT=$SERVICE_PORT|" .env
    sed -i "s|^DEBUG=.*|DEBUG=False|" .env
    sed -i "s|^APP_ENV=.*|APP_ENV=production|" .env
    
    # 如果 SECRET_KEY 和 JWT_SECRET_KEY 存在，则更新
    if grep -q "^SECRET_KEY=" .env; then
        sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|" .env
    else
        echo "SECRET_KEY=$SECRET_KEY" >> .env
    fi
    
    if grep -q "^JWT_SECRET_KEY=" .env; then
        sed -i "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$JWT_SECRET_KEY|" .env
    else
        echo "JWT_SECRET_KEY=$JWT_SECRET_KEY" >> .env
    fi
    
    print_success "环境变量配置完成"
    print_info "密钥已自动生成并保存到 .env 文件"
}

# 初始化数据库
init_database() {
    print_info "初始化数据库..."
    cd "$BACKEND_DIR"
    
    source venv/bin/activate
    
    if ! python scripts/init_db.py; then
        print_error "数据库初始化失败"
        exit 1
    fi
    
    print_success "数据库初始化完成"
}

# 创建管理员用户
create_admin_user() {
    print_info "创建管理员用户..."
    cd "$BACKEND_DIR"
    
    source venv/bin/activate
    
    # 检查是否已有用户
    if python3 -c "from app.database import SessionLocal, User; db = SessionLocal(); users = db.query(User).count(); print(users)" 2>/dev/null | grep -q "^0$"; then
        print_warning "数据库中暂无用户，需要创建管理员用户"
        print_info "请输入管理员用户名（默认: admin）:"
        read -r username
        username=${username:-admin}
        
        print_info "请输入管理员密码:"
        read -rs password
        if [ -z "$password" ]; then
            print_error "密码不能为空"
            exit 1
        fi
        
        print_info "确认密码:"
        read -rs password_confirm
        if [ "$password" != "$password_confirm" ]; then
            print_error "两次输入的密码不一致"
            exit 1
        fi
        
        if python scripts/create_user.py "$username" "$password"; then
            print_success "管理员用户创建成功: $username"
        else
            print_error "管理员用户创建失败"
            exit 1
        fi
    else
        print_info "数据库中已有用户，跳过创建"
    fi
}

# 创建 systemd 服务
setup_systemd_service() {
    print_info "创建 systemd 服务..."
    
    # 检查服务是否已存在
    if [ -f "/etc/systemd/system/$SERVICE_NAME.service" ]; then
        print_warning "服务文件已存在，是否覆盖？(y/n)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            print_info "保留现有服务文件"
            return
        fi
    fi
    
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
    
    # 重新加载 systemd
    systemctl daemon-reload
    
    print_success "systemd 服务创建完成"
}

# 启动服务
start_service() {
    print_info "启动服务..."
    
    # 停止现有服务（如果运行中）
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_info "停止现有服务..."
        systemctl stop "$SERVICE_NAME"
    fi
    
    # 启用并启动服务
    systemctl enable "$SERVICE_NAME"
    systemctl start "$SERVICE_NAME"
    
    # 等待服务启动
    sleep 3
    
    # 检查服务状态
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_success "服务启动成功"
    else
        print_error "服务启动失败"
        print_info "查看日志: journalctl -u $SERVICE_NAME -n 50"
        exit 1
    fi
}

# 配置防火墙
setup_firewall() {
    print_info "配置防火墙..."
    
    if command -v ufw &> /dev/null; then
        # Ubuntu/Debian 使用 ufw
        if ufw status | grep -q "Status: active"; then
            if ! ufw status | grep -q "$SERVICE_PORT/tcp"; then
                ufw allow "$SERVICE_PORT/tcp"
                print_success "防火墙规则已添加: 允许端口 $SERVICE_PORT"
            else
                print_info "防火墙规则已存在"
            fi
        else
            print_info "UFW 防火墙未激活，跳过配置"
        fi
    elif command -v firewall-cmd &> /dev/null; then
        # CentOS/RHEL 使用 firewalld
        if firewall-cmd --state &> /dev/null; then
            firewall-cmd --permanent --add-port="$SERVICE_PORT/tcp"
            firewall-cmd --reload
            print_success "防火墙规则已添加: 允许端口 $SERVICE_PORT"
        else
            print_info "Firewalld 防火墙未运行，跳过配置"
        fi
    else
        print_warning "未检测到防火墙工具，请手动配置端口 $SERVICE_PORT"
    fi
}

# 验证部署
verify_deployment() {
    print_info "验证部署..."
    
    # 检查服务状态
    if ! systemctl is-active --quiet "$SERVICE_NAME"; then
        print_error "服务未运行"
        return 1
    fi
    
    # 等待服务完全启动
    sleep 2
    
    # 测试健康检查端点
    if command -v curl &> /dev/null; then
        if curl -s -f "http://localhost:$SERVICE_PORT/health" > /dev/null; then
            print_success "健康检查通过"
        else
            print_warning "健康检查失败，但服务可能仍在启动中"
        fi
    fi
    
    print_success "部署验证完成"
}

# 显示部署信息
show_deployment_info() {
    echo ""
    echo "=========================================="
    print_success "部署完成！"
    echo "=========================================="
    echo ""
    echo "服务信息:"
    echo "  服务名称: $SERVICE_NAME"
    echo "  服务端口: $SERVICE_PORT"
    echo "  服务地址: http://112.124.2.164:$SERVICE_PORT"
    echo ""
    echo "访问地址:"
    echo "  前端页面: http://112.124.2.164:$SERVICE_PORT/"
    echo "  API 文档: http://112.124.2.164:$SERVICE_PORT/docs"
    echo "  健康检查: http://112.124.2.164:$SERVICE_PORT/health"
    echo ""
    echo "服务管理命令:"
    echo "  查看状态: systemctl status $SERVICE_NAME"
    echo "  查看日志: journalctl -u $SERVICE_NAME -f"
    echo "  重启服务: systemctl restart $SERVICE_NAME"
    echo "  停止服务: systemctl stop $SERVICE_NAME"
    echo "  启动服务: systemctl start $SERVICE_NAME"
    echo ""
    print_info "如需创建更多用户，请运行:"
    echo "  cd $BACKEND_DIR"
    echo "  source venv/bin/activate"
    echo "  python scripts/create_user.py <用户名> <密码>"
    echo ""
}

# 主函数
main() {
    echo "=========================================="
    echo "学习资料聚合平台 - 自动部署脚本"
    echo "=========================================="
    echo ""
    
    # 执行部署步骤
    check_root
    check_python
    check_project_dir
    setup_venv
    install_dependencies
    setup_env
    init_database
    
    # 询问是否创建管理员用户
    echo ""
    print_info "是否现在创建管理员用户？(y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        create_admin_user
    else
        print_info "跳过用户创建，稍后可以运行:"
        print_info "  cd $BACKEND_DIR && source venv/bin/activate"
        print_info "  python scripts/create_user.py admin your_password"
    fi
    
    setup_systemd_service
    setup_firewall
    start_service
    verify_deployment
    show_deployment_info
}

# 运行主函数
main "$@"
