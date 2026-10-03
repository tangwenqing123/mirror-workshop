#!/usr/bin/env bash
# 镜像工坊·启动ComfyUI(幂等): GPU机自动用GPU, 无GPU降级--cpu。
# 对外暴露(AutoDL"自定义服务"走6006): COMFY_PUBLIC=1 COMFY_PORT=6006 bash scripts/start_comfy.sh
HERE="$(cd "$(dirname "$0")" && pwd)"
MIRROR="$(dirname "$HERE")"
LOG="$MIRROR/logs"; mkdir -p "$LOG"
PORT="${COMFY_PORT:-8188}"
if curl -s -o /dev/null -m 2 "http://127.0.0.1:$PORT/"; then
  echo "[skip] ComfyUI已在$PORT"; exit 0
fi
cd "$MIRROR/ComfyUI" || { echo "[fail] 无ComfyUI,先跑bootstrap_env.sh"; exit 1; }
ARGS="--listen 127.0.0.1 --port $PORT"
if [ "${COMFY_PUBLIC:-0}" = "1" ]; then ARGS="--listen 0.0.0.0 --port $PORT"; fi
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
  echo "[gpu] 检测到GPU, GPU模式"
else
  ARGS="$ARGS --cpu"; echo "[cpu] 无GPU, CPU模式(仅烟测)"
fi
nohup python main.py $ARGS > "$LOG/comfy.log" 2>&1 &
echo $! > "$LOG/comfy.pid"
for i in $(seq 1 30); do
  curl -s -o /dev/null -m 2 "http://127.0.0.1:$PORT/" && { echo "[ok] ComfyUI up :$PORT (pid $(cat "$LOG/comfy.pid"))"; exit 0; }
  sleep 2
done
echo "[fail] 看logs/comfy.log"; exit 1
