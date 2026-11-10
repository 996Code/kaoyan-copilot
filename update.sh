#!/bin/bash
# 服务器一键更新：git pull + 重新部署
# 用法：cd /data/kaoyan-copilot/src && ./update.sh
# （或加 alias：alias kaoyan-update='cd /data/kaoyan-copilot/src && ./update.sh'）

cd "$(dirname "$0")"
git pull

HOST_ASSETS_DIR=/data/kaoyan-copilot/data/assets \
NETWORK=llm-modeler_default \
PORT=28080 \
APP_PREFIX=/kaoyan \
VITE_BASE=/kaoyan/ \
bash deploy.sh
