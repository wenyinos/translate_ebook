#!/bin/bash

# 电子书翻译脚本 - 快捷运行脚本

set -e

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "虚拟环境不存在，正在创建..."
    bash setup_venv.sh
fi

# 激活虚拟环境
source venv/bin/activate

# 运行翻译脚本
python translate.py "$@"
