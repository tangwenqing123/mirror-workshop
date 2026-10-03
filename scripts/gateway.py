#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""镜像工坊·统一网关 v0 —— 探针+路由占位。端口9000。
  /health        本网关存活
  /comfy/status  ComfyUI(8188) 是否在
  /vllm/status   vLLM(8000) 是否在(T002后生效)
  /disk          mirror目录自算用量 vs 预算(云上df是1P大盘,个人配额100GB,勿信df)
"""
import os, time, urllib.request
from fastapi import FastAPI
import uvicorn

HERE = os.path.dirname(os.path.abspath(__file__))
MIRROR_ROOT = os.environ.get("MIRROR_ROOT", os.path.dirname(HERE))
BUDGET_GB = float(os.environ.get("MIRROR_BUDGET_GB", "85"))
app = FastAPI(title="mirror-gateway", version="0.1")


def probe(url, timeout=2):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status
    except Exception:
        return None


def du_gb(path):
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return round(total / 1e9, 2)


@app.get("/health")
def health():
    return {"status": "ok", "ts": int(time.time()), "version": "0.1"}


@app.get("/comfy/status")
def comfy():
    code = probe("http://127.0.0.1:8188/")
    return {"up": code is not None, "code": code}


@app.get("/vllm/status")
def vllm():
    code = probe("http://127.0.0.1:8000/v1/models")
    return {"up": code is not None, "code": code}


@app.get("/disk")
def disk():
    used = du_gb(MIRROR_ROOT)
    return {"root": MIRROR_ROOT, "used_gb": used, "budget_gb": BUDGET_GB,
            "over": used > BUDGET_GB, "note": "平台个人配额100GB, 超限会被清理"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9000, log_level="warning")
