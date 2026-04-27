FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量，防止 python 写入 pyc 文件，并强制无缓冲输出
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 复制依赖文件
COPY requirements.txt .

# 在有网的构建阶段安装依赖包（这里使用清华源加速）
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目所有代码到容器中 (受 .dockerignore 控制)
COPY . .

# 暴露 FastAPI 的默认端口
EXPOSE 8000

# 健康检查：每 30 秒探测一次结构化健康检查接口，连续 3 次失败则标记为 unhealthy
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')" || exit 1

# 启动命令
CMD ["python", "main.py"]
