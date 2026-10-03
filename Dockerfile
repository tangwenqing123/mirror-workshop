# 镜像工坊·环境镜像（形态B: AutoDL租卡/公开发布用）
# ★ 许可红线: 本镜像只含环境+脚本, 不打包任何模型权重(H3社区许可禁止权重二次分发)。
#   权重由使用者自行下载: python scripts/dl_weights.py --all (落在挂载卷, 不进镜像层)
FROM pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime
WORKDIR /workspace
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple || pip install --no-cache-dir -r requirements.txt
COPY scripts/ ./scripts/
ENV MIRROR_ROOT=/workspace MIRROR_BUDGET_GB=85
EXPOSE 8188 9000
CMD ["bash", "scripts/start_all.sh"]
# 用法(AutoDL自定义镜像/任意dockerd):
#   docker build -t mirror-workshop .
#   docker run -d -p 9000:9000 -v /path/to/weights:/workspace/models mirror-workshop
