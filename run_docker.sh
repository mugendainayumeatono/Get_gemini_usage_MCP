#!/bin/bash

# 设置镜像名称
IMAGE_NAME="gcp-token-usage-mcp"
FORCE_BUILD=false

# 解析输入参数
DEBUG_MODE=""
DOCKER_DAEMON_FLAG="-d"
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -b|--build) FORCE_BUILD=true; shift ;;
        -d|--debug) 
            DEBUG_MODE="-e MCP_DEBUG=true"
            DOCKER_DAEMON_FLAG=""
            shift 
            ;;
        *) echo "未知参数: $1"; exit 1 ;;
    esac
done

# 检查镜像是否存在，如果不存在或者需要强制构建则执行构建
if [[ "$FORCE_BUILD" == true ]] || [[ "$(docker images -q $IMAGE_NAME 2> /dev/null)" == "" ]]; then
  # 生成基于时间戳的版本号，如 v20240501-123456
  VERSION="v$(date +%Y%m%d-%H%M%S)"
  echo "正在构建镜像 $IMAGE_NAME:$VERSION ..."
  # 添加 --no-cache 确保每次强制构建都是干净的（可选，这里保持普通构建）
  # 同时打上 latest 和具体的版本号 tag
  docker build -t $IMAGE_NAME:latest -t $IMAGE_NAME:$VERSION .
  echo "镜像构建完成，已标记为 latest 和 $VERSION"
fi

# 检查是否存在 .env 文件并导出变量
if [ -f .env ]; then
  echo "检测到 .env 文件，正在加载环境变量..."
  export $(grep -v '^#' .env | xargs)
fi

# 设置凭据路径
if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
  CREDENTIALS_FILE="$GOOGLE_APPLICATION_CREDENTIALS"
  echo "使用环境变量中定义的凭据: $CREDENTIALS_FILE"
else
  # 默认使用 Google Cloud SDK 的标准 ADC 路径
  CREDENTIALS_FILE="$HOME/.config/gcloud/application_default_credentials.json"
  echo "未定义 GOOGLE_APPLICATION_CREDENTIALS，尝试使用默认 ADC 路径..."
fi

# 检查凭据文件是否存在
if [ ! -f "$CREDENTIALS_FILE" ]; then
  echo "错误: 未找到凭据文件: $CREDENTIALS_FILE"
  if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "请先运行: gcloud auth application-default login"
  fi
  exit 1
fi

echo "正在启动 MCP 服务器容器 (Streamable HTTP 模式)..."

# 启动容器
# 将凭据文件挂载到容器内的固定位置，映射端口，并设置环境变量
# 同时传递 TEST_PROJECT_ID 如果它在 .env 中设置了
docker run $DOCKER_DAEMON_FLAG -p 8000:8000 --rm \
  -v "$CREDENTIALS_FILE:/app/credentials.json:ro" \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
  -e TEST_PROJECT_ID="$TEST_PROJECT_ID" \
  $DEBUG_MODE \
  $IMAGE_NAME
