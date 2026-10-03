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

## 🏭 产线迁移（2026-10-03 起：漫剧/内容批量出货全走本实例）

**姿态**：实例按需开机（¥1.68/时 4080S-32G）， zealman 镜像 43 张 API 卡 = 产能目录（工作台「🎬GPU工坊」页签可视化）；模型全在 AutoDL 共享仓库软链挂载，**永不自己下载权重**。

**统一客户端**（本地，隧道自动建立 16008→6008）：
```
python scripts/studio_client.py status            # 实例/队列状态
python scripts/studio_client.py list              # 43卡清单
python scripts/studio_client.py card API-A01-文生图-Qwen2512高清放大
python scripts/studio_client.py call --wf API-A01-文生图-Qwen2512高清放大 --set "187:text=提示词" --out out.png
python scripts/studio_client.py batch payload.json
python scripts/studio_client.py put 本地 /root/ComfyUI/input/ep_batch/refs/x.png
```

**四层产能**：
| 层 | 主力卡 | 状态 |
|---|---|---|
| 视频 | U03文生加速(2.5min/段) / U02图生 / U08全能参考(多图+台词直写) | ✅ EP09全10段+EP10批量实跑 |
| 图片 | A01文生图 / C16短剧文生图 / C19三视图 / D20画质重建 | ✅ 两场景资产实跑(各~1.5min) |
| 配音 | N2单人声音克隆(FishAudio) / N01多 / N03双 | 卡就绪待业务调用 |
| 音乐 | 主力=Music3免费API(不动)；备胎=ACE-Step v1.5三权重已挂载，N05工作流待导入卡 | 备胎就绪 |

**已验证批量配方（漫剧 EP09/EP10）**：tools/build_ep_batch_payload.py（参考图+时长+RH Enhanced提示词打包）→ tools/batch_ep_gpu.py（实例端断点续跑批量器）→ clips 拉回 → build_timeline → tools/render_timeline_v2.py（concat+混音+ASS+loudnorm −14LUFS）→ 成片。
**踩坑**：LoadImage 缺图=HTTP 422 且会杀死旧驱动器（已修=单段容错）；ModelScope 免费出图通道限额后 task 全拒（task not found）→ 场景资产改走 GPU A01 卡；EP09 时间线脚本 E08 命名复制遗留已修；ass 滤镜 Windows 盘符冒号须转义。
