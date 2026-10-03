#!/usr/bin/env bash
# 镜像工坊·一键启动: 环境自检(幂等) -> ComfyUI(8188) -> 网关(9000)
HERE="$(cd "$(dirname "$0")" && pwd)"
MIRROR="$(dirname "$HERE")"
LOG="$MIRROR/logs"; mkdir -p "$LOG"
bash "$HERE/bootstrap_env.sh"
bash "$HERE/start_comfy.sh"
if curl -s -o /dev/null -m 2 http://127.0.0.1:9000/health; then
  echo "[skip] 网关已在9000"
else
  nohup python "$HERE/gateway.py" > "$LOG/gateway.log" 2>&1 &
  echo $! > "$LOG/gateway.pid"; sleep 3
fi
curl -s http://127.0.0.1:9000/health && echo && \
curl -s http://127.0.0.1:9000/disk && echo && echo "[done] 镜像工坊在线: 网关9000 / ComfyUI 8188"
