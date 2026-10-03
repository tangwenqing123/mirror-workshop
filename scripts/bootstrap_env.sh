#!/usr/bin/env bash
# 镜像工坊·环境安装(幂等): ComfyUI + 网关依赖。重跑不重复安装。
# 纪律: 不装会替换torch的大包(vllm等归T002/GPU阶段); 用镜像自带系统python。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
MIRROR="$(dirname "$HERE")"
LOG="$MIRROR/logs"; mkdir -p "$LOG"
PIP="${PIP_INDEX:-}"   # 可 export PIP_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple
pipin() { pip install $PIP "$@" >>"$LOG/pip.log" 2>&1; }

clone_gh() { # clone_gh <url> <dest> : github直连->ghproxy->gitclone 三连降级
  local url="$1" dest="$2"
  [ -d "$dest/.git" ] && { echo "[skip] 已存在 $dest"; return 0; }
  git clone --depth 1 "$url" "$dest" 2>>"$LOG/git.log" && return 0
  git clone --depth 1 "https://gh-proxy.com/$url" "$dest" 2>>"$LOG/git.log" && return 0
  git clone --depth 1 "https://gitclone.com/github.com/${url#https://github.com/}" "$dest" 2>>"$LOG/git.log"
}

echo "== 1/3 ComfyUI =="
clone_gh "https://github.com/comfyanonymous/ComfyUI.git" "$MIRROR/ComfyUI" || echo "[warn] ComfyUI clone失败,看git.log"
if [ -f "$MIRROR/ComfyUI/requirements.txt" ]; then
  grep -viE '^\s*torch' "$MIRROR/ComfyUI/requirements.txt" > "$LOG/req_no_torch.txt"
  pipin -r "$LOG/req_no_torch.txt" || echo "[warn] comfy依赖部分失败,明细pip.log"
fi

echo "== 2/3 网关依赖 =="
python -c "import fastapi, uvicorn" 2>/dev/null || pipin fastapi uvicorn || echo "[warn] fastapi安装失败"
python -c "import requests" 2>/dev/null || pipin requests

echo "== 3/3 自检 =="
python -c "import fastapi, uvicorn, requests; print('[ok] 依赖齐')" 2>/dev/null || echo "[fail] 依赖缺"
[ -d "$MIRROR/ComfyUI" ] && echo "[ok] ComfyUI就位: $MIRROR/ComfyUI" || echo "[fail] ComfyUI缺"
echo "bootstrap完成(幂等,可重跑)"
