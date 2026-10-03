#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""镜像工坊·权重下载器 v0（幂等 + 断点续传 + 磁盘预算闸门）

用法:
  python dl_weights.py --plan                 # 只探测/列选型计划，不下载
  python dl_weights.py --all                  # 按序下载全部合格模型
  python dl_weights.py --only h3              # 只下指定: h3|qwen_image|cosyvoice2
  python dl_weights.py --set h3=MiniMax/MiniMax-H3-FP8   # 手动指定候选仓(选型失败时用)

规则(与设计文档一致):
  - 只下 FP8/量化版; 合格=体积已知且 <= hard_cap; cap=0 表示"仅展示禁止下载"(如bf16全量)
  - 磁盘预算: mirror目录自算用量 + 新增 <= MIRROR_BUDGET_GB(默认85) —— 注意云上df的1P是
    阿里大盘, 个人配额100GB, 所以预算按"自己目录的du"算, 不看磁盘剩余!
  - 断点续传: modelscope SDK 自带; HF单文件走 Range 续传
  - 令牌: 只从 --token-file 运行时读(正则提ms-前缀), 禁止写入任何文件/日志
"""
import argparse, json, os, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
MIRROR_ROOT = os.environ.get("MIRROR_ROOT", os.path.dirname(HERE))
MODELS_DIR = os.path.join(MIRROR_ROOT, "models")
MANIFEST = os.path.join(MODELS_DIR, "MANIFEST.json")
BUDGET_GB = float(os.environ.get("MIRROR_BUDGET_GB", "85"))
HF_MIRROR = os.environ.get("HF_ENDPOINT", "https://hf-mirror.com")

# name -> [ (platform, repo_id, subpath, expect_gb, hard_cap_gb) ]  按优先序
# H3量化来源=ComfyUI官方转存仓(实测HEAD 2026-10-03): FL2VA=文生/图生视频, Ref2VA=参考图驱动(角色一致性)
CANDIDATES = {
    "h3": [
        ("hf", "Comfy-Org/MiniMax-H3",
         "diffusion_models/minimax_h3_fl2va_pruned_fp8_scaled.safetensors", 21, 25),
        ("modelscope", "MiniMax/MiniMax-H3", None, 498, 0),   # bf16四变体全量: 仅展示禁止
    ],
    "h3_r2v": [   # 可选(不在--all默认清单): R2V多图参考工作流
        ("hf", "Comfy-Org/MiniMax-H3",
         "diffusion_models/minimax_h3_ref2va_pruned_fp8_scaled.safetensors", 21, 25),
    ],
    "qwen_image": [
        ("hf", "Comfy-Org/Qwen-Image_ComfyUI",
         "split_files/diffusion_models/qwen_image_fp8_e4m3fn.safetensors", 18, 25),
        ("modelscope", "Qwen/Qwen-Image", None, 40, 0),       # bf16全量: 只展示不下
    ],
    "cosyvoice2": [
        ("modelscope", "iic/CosyVoice2-0.5B", None, 5, 8),
    ],
}
ALL_ORDER = ["h3", "qwen_image", "cosyvoice2"]   # --all 默认清单(h3_r2v 用 --only 单独下)
GIT_CODE = {"cosyvoice2": "https://github.com/FunAudioLLM/CosyVoice2.git"}


def http_json(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "mirror-dl/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))


def ms_model_size_gb(repo):
    """魔搭仓体积: /api/v1/models/{repo}/repo/files 递归求和(blob)。失败返回None"""
    try:
        d = http_json("https://modelscope.cn/api/v1/models/%s/repo/files?Revision=master&Recursive=true" % repo)
        files = (d.get("Data") or {}).get("Files") or []
        total = sum(int(f.get("Size") or 0) for f in files if f.get("Type") in (None, "blob"))
        return total / 1e9 if total else None
    except Exception:
        return None


def hf_file_size_gb(repo, subpath):
    """HF(走镜像)单文件体积: HEAD resolve 取 Content-Length。失败返回None"""
    url = "%s/%s/resolve/main/%s" % (HF_MIRROR, repo, subpath)
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "mirror-dl/0.1"})
        with urllib.request.urlopen(req, timeout=20) as r:
            n = r.headers.get("Content-Length")
            return int(n) / 1e9 if n else None
    except Exception:
        return None


def dir_size_gb(path):
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total / 1e9


def load_manifest():
    try:
        return json.load(open(MANIFEST, encoding="utf-8"))
    except Exception:
        return {}


def save_manifest(m):
    os.makedirs(MODELS_DIR, exist_ok=True)
    json.dump(m, open(MANIFEST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def pick(name, overrides):
    """返回 (选中的candidate|None, 探测报告列表)"""
    cands = list(CANDIDATES.get(name, []))
    if name in overrides:
        cands.insert(0, ("modelscope" if "/" in overrides[name] and ":" not in overrides[name] else "hf",
                         overrides[name], None, 999, 45))
    report, ok = [], None
    for platform, repo, sub, expect, cap in cands:
        size = (ms_model_size_gb(repo) if platform == "modelscope" else hf_file_size_gb(repo, sub)) if sub or platform == "modelscope" else None
        tag = "OK选中" if (cap > 0 and size is not None and size <= cap) else \
              ("禁止(bf16超预算)" if cap == 0 else ("体积未知" if size is None else "超cap"))
        report.append("  [%s] %s %s 期望~%sGB 实测%.1fGB cap=%s -> %s" %
                      (platform, repo, sub or "(整仓)", expect, size if size else -1, cap or "-", tag))
        if ok is None and tag == "OK选中":
            ok = (platform, repo, sub, size)
    return ok, report


def dl_modelscope(repo, dest):
    from modelscope import snapshot_download  # 延迟导入,plan模式零依赖
    tok = os.environ.get("MIRROR_MS_TOKEN") or None
    snapshot_download(repo, local_dir=dest, revision="master", token=tok)


def dl_hf_file(repo, sub, dest):
    os.makedirs(dest, exist_ok=True)
    part = os.path.join(dest, os.path.basename(sub) + ".part")
    final = os.path.join(dest, os.path.basename(sub))
    if os.path.exists(final):
        print("    已存在跳过:", final); return
    url = "%s/%s/resolve/main/%s" % (HF_MIRROR, repo, sub)
    done = os.path.getsize(part) if os.path.exists(part) else 0
    req = urllib.request.Request(url, headers={"User-Agent": "mirror-dl/0.1", "Range": "bytes=%d-" % done})
    with urllib.request.urlopen(req, timeout=60) as r, open(part, "ab") as f:
        while True:
            chunk = r.read(1 << 22)
            if not chunk:
                break
            f.write(chunk)
    os.replace(part, final)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true", help="只列计划不下载")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--only", help="h3|qwen_image|cosyvoice2")
    ap.add_argument("--set", action="append", default=[], help="name=repo_id 手动加候选")
    a = ap.parse_args()
    overrides = dict(x.split("=", 1) for x in getattr(a, "set"))
    targets = [a.only] if a.only else (ALL_ORDER if a.all or a.plan else [])
    if not targets:
        print(__doc__); return
    used = dir_size_gb(MIRROR_ROOT)
    print("== 镜像工坊选型计划 ==  mirror已用 %.1fGB / 预算 %sGB" % (used, BUDGET_GB))
    man = load_manifest()
    for name in targets:
        ok, report = pick(name, overrides)
        print("· %s:" % name)
        print("\n".join(report))
        if ok is None:
            if not a.plan:
                man[name] = {"status": "skipped", "ts": time.time()}
            print("  -> 跳过(可 --set %s=组织/仓 手动指定后重跑)" % name)
            continue
        platform, repo, sub, size = ok
        plan_gb = used + size
        print("  -> 选定 %s/%s (%.1fGB), 下完后预计 %.1fGB" % (platform, repo, size, plan_gb))
        if plan_gb > BUDGET_GB:
            print("  !! 超预算 %sGB, 停止(可用 MIRROR_BUDGET_GB 调,但100GB是平台红线)" % BUDGET_GB)
            continue
        if a.plan:
            continue
        dest = os.path.join(MODELS_DIR, name)
        t0 = time.time()
        try:
            if platform == "modelscope" and sub is None:
                dl_modelscope(repo, dest)
            elif sub:
                dl_hf_file(repo, sub, dest)
            else:
                raise RuntimeError("该候选需要整仓下载但平台不是modelscope: %s" % platform)
            if name in GIT_CODE:
                code_dir = os.path.join(MIRROR_ROOT, "code", name)
                if not os.path.isdir(code_dir):
                    os.makedirs(os.path.dirname(code_dir), exist_ok=True)
                    os.system('git clone "%s" "%s" || git clone "https://gh-proxy.com/%s" "%s"'
                              % (GIT_CODE[name], code_dir, GIT_CODE[name], code_dir))
            man[name] = {"status": "ok", "platform": platform, "repo": repo,
                         "path": dest, "gb": round(size, 1), "ts": time.time()}
            print("  完成, 用时 %.0f 分钟" % ((time.time() - t0) / 60))
        except Exception as e:
            man[name] = {"status": "error", "repo": repo, "err": str(e)[:300], "ts": time.time()}
            print("  失败:", e)
        save_manifest(man)
    if not a.plan:
        save_manifest(man)
    print("== MANIFEST ->", MANIFEST if not a.plan else "(干跑未写)")


if __name__ == "__main__":
    main()
