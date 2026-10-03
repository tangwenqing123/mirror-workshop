# 镜像工坊 mirror-workshop

自建 GPU 内容工坊：视频(H3) / 图片(Qwen-Image) / 配音(CosyVoice2) / 垂直模型(vLLM) / 统一网关。
一套代码两种形态，出活不依赖买 API 额度。设计档：`../hot/立项_镜像工坊_2026-10-03.md`。

## 磁盘纪律（最重要）
- 魔搭 `/mnt/workspace` 个人配额 **100GB**（`df` 显示的 1P 是阿里大盘，别被骗）
- 看自己用量：`python scripts/gateway.py` 起来后 `curl 127.0.0.1:9000/disk`，或 `du -sh`
- 预算闸门默认 85GB（`MIRROR_BUDGET_GB` 可调，100 是平台红线）

## 形态A：魔搭 NoteBook（免费额度验证）
```bash
cd /mnt/workspace && git clone <本仓> mirror && cd mirror
python scripts/dl_weights.py --plan        # 先看选型,不下
python scripts/dl_weights.py --all         # 下载(断点续传,实例8h自动关机也能分窗攒)
bash scripts/start_all.sh                  # ComfyUI:8188 + 网关:9000
```

## 形态B：AutoDL 租卡（长期自用）
```bash
# 1. 租 4090 → 终端里 git clone 本仓 → bash scripts/start_all.sh
# 2. python scripts/dl_weights.py --all     # 权重下到数据盘 /root/autodl-tmp(持久)
# 3. 关机前: 更多 → 保存镜像  = 你的私人长期镜像, 以后开机直接选
```

## 脚本一览
| 脚本 | 作用 |
|---|---|
| `scripts/dl_weights.py` | 权重下载：FP8优先/预算闸门/断点续传/MANIFEST 记账；`--plan` 只看不下 |
| `scripts/bootstrap_env.sh` | 幂等装 ComfyUI+网关依赖（三连降级 clone，防墙） |
| `scripts/start_comfy.sh` | 起 ComfyUI :8188（幂等） |
| `scripts/gateway.py` | 网关 :9000（/health /comfy/status /vllm/status /disk） |
| `scripts/start_all.sh` | 一键全起 |
| `Dockerfile` | 形态B 公开版：只含环境+下载器，**不含权重** |

## 许可红线（务必遵守）
- MiniMax H3 社区许可：年收入 < $2000 万可商用须**署名 "MiniMax H3"**；**禁止权重二次分发**（公开镜像/数据集不带权重）；**禁止用 H3 输出训练其他模型**（成片勿回填训练集）
- 权重来源与许可以 [MiniMax-AI/MiniMax-H3](https://github.com/MiniMax-AI/MiniMax-H3) 官方仓为准

## 路线
T001 本地骨架(本仓) → T002 GPU 验证 H3 出首条片(计时) → T003 AutoDL 保存私人镜像 → (可选)公开镜像赚激励
