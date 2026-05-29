#!/bin/bash

# 电子书翻译脚本 - 虚拟环境设置脚本

set -e

echo "=== 电子书翻译脚本 - 环境设置 ==="

# 检查 Python 版本
echo "检查 Python 版本..."
python3 --version

# 创建虚拟环境
echo "创建虚拟环境..."
python3 -m venv venv

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 升级 pip
echo "升级 pip..."
pip install --upgrade pip

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt

# 创建配置文件（如果不存在）
if [ ! -f config.env ]; then
    echo "创建配置文件..."
    cp config.env.example config.env
    echo "请编辑 config.env 文件，填入你的 API Key"
fi

# 设置脚本权限
chmod +x translate.py

echo ""
echo "=== 设置完成 ==="
echo "使用方法："
echo "1. 激活虚拟环境: source venv/bin/activate"
echo "2. 编辑配置文件: nano config.env"
echo "3. 运行翻译: python translate.py <文件路径>"
echo ""
echo "或直接使用: ./run.sh <文件路径>"
