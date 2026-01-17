#!/bin/bash
# 修复部署脚本 - 处理虚拟环境创建问题

set -e

cd /opt/Learning\ Archive\ Platform/backend

echo "=========================================="
echo "修复虚拟环境..."
echo "=========================================="

# 如果虚拟环境存在但有问题，删除它
if [ -d "venv" ]; then
    echo "删除旧的虚拟环境..."
    rm -rf venv
fi

# 创建新的虚拟环境
echo "创建新的虚拟环境..."
python3 -m venv venv

# 验证虚拟环境
if [ ! -f "venv/bin/activate" ]; then
    echo "错误: 虚拟环境创建失败！"
    exit 1
fi

echo "虚拟环境创建成功！"
echo ""
echo "现在可以继续执行以下步骤："
echo ""
echo "1. 激活虚拟环境并安装依赖："
echo "   source venv/bin/activate"
echo "   pip install --upgrade pip"
echo "   pip install -r requirements.txt"
echo ""
echo "2. 配置环境变量："
echo "   cp .env.example .env"
echo "   nano .env  # 编辑配置"
echo ""
echo "3. 初始化数据库："
echo "   python scripts/init_db.py"
echo ""
echo "4. 创建管理员用户："
echo "   python scripts/create_user.py admin your_password"
echo ""
