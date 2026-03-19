# 使用轻量级的 Python 3.10 镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源代码
COPY mcp_server.py .
COPY test/ ./test/

# 暴露端口（Streamable HTTP 模式需要）
EXPOSE 8000

# 运行 MCP 服务器
# 使用 -u 确保日志实时输出
ENTRYPOINT ["python", "-u", "mcp_server.py"]
