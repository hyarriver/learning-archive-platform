#!/bin/bash
# 完整部署脚本 - 从当前位置开始执行

set -e  # 遇到错误立即退出

echo "=========================================="
echo "开始完整部署流程"
echo "=========================================="

# 进入 backend 目录
cd /opt/Learning\ Archive\ Platform/backend

# 步骤 1: 确保虚拟环境已激活
if [ -z "$VIRTUAL_ENV" ]; then
    echo "[1/10] 激活虚拟环境..."
    source venv/bin/activate
else
    echo "[1/10] 虚拟环境已激活"
fi

# 步骤 2: 安装依赖
echo "[2/10] 安装 Python 依赖..."
pip install --upgrade pip -q
pip install -r requirements.txt

# 步骤 3: 创建目录
echo "[3/10] 创建必要的目录..."
mkdir -p data logs

# 步骤 4: 配置环境变量
echo "[4/10] 配置环境变量..."
if [ ! -f .env ]; then
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    
    cat > .env <<EOF
APP_NAME=Learning Archive Platform
APP_ENV=production
DEBUG=False
SECRET_KEY=$SECRET_KEY
JWT_SECRET_KEY=$JWT_SECRET_KEY
HOST=0.0.0.0
PORT=3000
DATABASE_URL=sqlite:///./data/archive.db
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
DATA_DIR=./data
COLLECTIONS_DIR=./data/collections
UPLOADS_DIR=./data/uploads
SCHEDULER_TIMEZONE=Asia/Shanghai
COLLECTION_SCHEDULE_HOUR=0
COLLECTION_SCHEDULE_MINUTE=0
CRAWLER_USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
CRAWLER_REQUEST_DELAY=1.0
CRAWLER_MAX_RETRIES=3
LOG_LEVEL=INFO
LOG_DIR=./logs
EOF
    echo "  .env 文件已创建，密钥已自动生成"
else
    echo "  .env 文件已存在，跳过创建"
    # 更新关键配置
    sed -i 's/^PORT=.*/PORT=3000/' .env
    sed -i 's/^DEBUG=.*/DEBUG=False/' .env
fi

# 步骤 5: 初始化数据库
echo "[5/10] 初始化数据库..."
python scripts/init_db.py

# 步骤 6: 创建管理员用户（可选）
echo "[6/10] 创建管理员用户..."
echo "  是否创建管理员用户？(y/n)"
read -r create_user
if [[ "$create_user" =~ ^[Yy]$ ]]; then
    echo "  请输入用户名（默认: admin）:"
    read -r username
    username=${username:-admin}
    
    echo "  请输入密码:"
    read -rs password
    if [ -n "$password" ]; then
        python scripts/create_user.py "$username" "$password"
        echo "  用户创建成功: $username"
    else
        echo "  跳过用户创建"
    fi
else
    echo "  跳过用户创建，稍后可以运行:"
    echo "    python scripts/create_user.py admin your_password"
fi

# 步骤 7: 创建 systemd 服务
echo "[7/10] 创建 systemd 服务..."
cat > /etc/systemd/system/archive-platform.service <<EOF
[Unit]
Description=Learning Archive Platform API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/Learning Archive Platform/backend
Environment="PATH=/opt/Learning Archive Platform/backend/venv/bin"
ExecStart=/opt/Learning Archive Platform/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 3000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
echo "  服务文件已创建"

# 步骤 8: 启动服务
echo "[8/10] 启动服务..."
systemctl enable archive-platform
systemctl start archive-platform
sleep 3

if systemctl is-active --quiet archive-platform; then
    echo "  服务启动成功"
else
    echo "  服务启动失败，查看日志:"
    journalctl -u archive-platform -n 20 --no-pager
    exit 1
fi

# 步骤 9: 配置防火墙
echo "[9/10] 配置防火墙..."
if command -v ufw &> /dev/null && ufw status | grep -q "Status: active"; then
    ufw allow 3000/tcp --quiet
    echo "  UFW 防火墙规则已添加"
elif command -v firewall-cmd &> /dev/null && firewall-cmd --state &> /dev/null; then
    firewall-cmd --permanent --add-port=3000/tcp --quiet
    firewall-cmd --reload --quiet
    echo "  Firewalld 防火墙规则已添加"
else
    echo "  防火墙未激活，跳过配置"
fi

# 步骤 10: 验证部署
echo "[10/10] 验证部署..."
sleep 2
if command -v curl &> /dev/null; then
    if curl -s -f http://localhost:3000/health > /dev/null; then
        echo "  健康检查通过"
    else
        echo "  健康检查失败，但服务可能仍在启动中"
    fi
fi

# 完成
echo ""
echo "=========================================="
echo "部署完成！"
echo "=========================================="
echo ""
echo "访问地址:"
echo "  前端页面: http://112.124.2.164:3000/"
echo "  API 文档: http://112.124.2.164:3000/docs"
echo "  健康检查: http://112.124.2.164:3000/health"
echo ""
echo "服务管理:"
echo "  查看状态: systemctl status archive-platform"
echo "  查看日志: journalctl -u archive-platform -f"
echo "  重启服务: systemctl restart archive-platform"
echo ""
