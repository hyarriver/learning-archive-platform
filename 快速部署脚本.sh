#!/bin/bash
# 学习资料聚合平台 - 快速部署脚本
# 服务器: 112.124.2.164:3000

set -e  # 遇到错误立即退出

echo "=========================================="
echo "学习资料聚合平台 - 服务器部署脚本"
echo "=========================================="

# 配置变量
PROJECT_DIR="/opt/Learning Archive Platform"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
SERVICE_NAME="archive-platform"
SERVICE_PORT=3000

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}请使用 root 用户运行此脚本${NC}"
    exit 1
fi

echo -e "${GREEN}步骤 1: 检查 Python 环境...${NC}"
if ! command -v python3 &> /dev/null; then
    echo "安装 Python 3..."
    if [ -f /etc/debian_version ]; then
        apt update
        apt install -y python3 python3-pip python3-venv
    elif [ -f /etc/redhat-release ]; then
        yum install -y python3 python3-pip
    else
        echo -e "${RED}无法检测系统类型，请手动安装 Python 3${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}步骤 2: 检查项目目录...${NC}"
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}项目目录不存在，请先上传项目文件到 $PROJECT_DIR${NC}"
    exit 1
fi

echo -e "${GREEN}步骤 3: 设置后端环境...${NC}"
cd "$BACKEND_DIR"

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    # 检查 python3-venv 是否安装
    if ! python3 -m venv venv 2>/dev/null; then
        echo -e "${YELLOW}虚拟环境创建失败，可能需要安装 python3-venv${NC}"
        echo "请运行: apt install python3.12-venv"
        echo "然后重新运行此脚本"
        exit 1
    fi
else
    echo -e "${YELLOW}虚拟环境已存在，跳过创建${NC}"
fi

# 激活虚拟环境并安装依赖
echo "安装 Python 依赖..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}步骤 4: 配置环境变量...${NC}"
if [ ! -f ".env" ]; then
    echo "创建 .env 文件..."
    cp .env.example .env
    
    # 生成随机密钥
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    
    # 更新 .env 文件
    sed -i "s|SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|" .env
    sed -i "s|JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$JWT_SECRET_KEY|" .env
    sed -i "s|PORT=.*|PORT=$SERVICE_PORT|" .env
    sed -i "s|DEBUG=.*|DEBUG=False|" .env
    sed -i "s|APP_ENV=.*|APP_ENV=production|" .env
    
    echo -e "${GREEN}.env 文件已创建，请检查并修改配置${NC}"
else
    echo -e "${YELLOW}.env 文件已存在，跳过${NC}"
fi

echo -e "${GREEN}步骤 5: 初始化数据库...${NC}"
python scripts/init_db.py

echo -e "${GREEN}步骤 6: 创建 systemd 服务...${NC}"
cat > /etc/systemd/system/$SERVICE_NAME.service <<EOF
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

echo -e "${GREEN}步骤 7: 配置防火墙...${NC}"
if command -v ufw &> /dev/null; then
    ufw allow $SERVICE_PORT/tcp
    echo "UFW 防火墙规则已添加"
elif command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-port=$SERVICE_PORT/tcp
    firewall-cmd --reload
    echo "Firewalld 防火墙规则已添加"
else
    echo -e "${YELLOW}未检测到防火墙，请手动配置端口 $SERVICE_PORT${NC}"
fi

echo -e "${GREEN}步骤 8: 启动服务...${NC}"
systemctl enable $SERVICE_NAME
systemctl restart $SERVICE_NAME
sleep 2
systemctl status $SERVICE_NAME --no-pager

echo ""
echo -e "${GREEN}=========================================="
echo "部署完成！"
echo "=========================================="
echo -e "${NC}"
echo "服务地址: http://112.124.2.164:$SERVICE_PORT"
echo "API 文档: http://112.124.2.164:$SERVICE_PORT/docs"
echo "健康检查: http://112.124.2.164:$SERVICE_PORT/health"
echo ""
echo "服务管理命令:"
echo "  查看状态: systemctl status $SERVICE_NAME"
echo "  查看日志: journalctl -u $SERVICE_NAME -f"
echo "  重启服务: systemctl restart $SERVICE_NAME"
echo "  停止服务: systemctl stop $SERVICE_NAME"
echo ""
echo -e "${YELLOW}重要: 请创建管理员用户${NC}"
echo "  cd $BACKEND_DIR"
echo "  source venv/bin/activate"
echo "  python scripts/create_user.py admin your_password"
echo ""
