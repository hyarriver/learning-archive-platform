#!/bin/bash
# 在服务器上直接执行此脚本

# 1. 进入项目目录
cd /opt/Learning\ Archive\ Platform

# 2. 下载/确认脚本存在并添加执行权限
if [ -f "智能自动部署脚本.sh" ]; then
    chmod +x 智能自动部署脚本.sh
    echo "脚本已存在，开始执行..."
    ./智能自动部署脚本.sh
elif [ -f "自动部署脚本.sh" ]; then
    chmod +x 自动部署脚本.sh
    echo "使用自动部署脚本..."
    ./自动部署脚本.sh
else
    echo "未找到部署脚本，请先上传脚本文件"
    exit 1
fi
