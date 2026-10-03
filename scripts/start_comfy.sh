#!/usr/bin/env bash
# 镜像工坊·启动ComfyUI(幂等): 已在监听8188则跳过。CPU模式可起,大模型加载归GPU阶段。
HERE="$(cd "$(dirname "$0")" && pwd)"
MIRROR="$(dirname "$HERE")"
LOG="$MIRROR/logs"; mkdir -p "$LOG"
if curl -s -o /dev/null -m 2 http://127.0.0.1:8188/; then
  echo "[skip] ComfyUI已在8188"; exit 0
fi
cd "$MIRROR/ComfyUI" || { echo "[fail] 无ComfyUI,先跑bootstrap_env.sh"; exit 1; }
nohup python main.py --listen 127.0.0.1 --port 8188 --cpu > "$LOG/comfy.log" 2>&1 &
echo $! > "$LOG/comfy.pid"
for i in $(seq 1 30); do
  curl -s -o /dev/null -m 2 http://127.0.0.1:8188/ && { echo "[ok] ComfyUI up (pid $(cat "$LOG/comfy.pid"))"; exit 0; }
  sleep 2
done
echo "[fail] 30次探测未起,看logs/comfy.log"; exit 1
