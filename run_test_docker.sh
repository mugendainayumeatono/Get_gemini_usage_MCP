#!/bin/bash

# 设置镜像名称
IMAGE_NAME="google-token-usage-test"
# 生成基于时间戳的版本号
VERSION="v$(date +%Y%m%d-%H%M%S)"

# 检查是否存在 .env 文件并导出变量
if [ -f .env ]; then
  echo "检测到 .env 文件，正在加载环境变量..."
  export $(grep -v '^#' .env | xargs)
fi

# 检查是否配置了测试项目 ID
if [ -z "$TEST_PROJECT_ID" ]; then
  TEST_PROJECT_ID="fake-project"
  echo "未设置 TEST_PROJECT_ID 环境变量，将使用默认值: $TEST_PROJECT_ID"
else
  echo "使用环境变量中定义的测试项目 ID: $TEST_PROJECT_ID"
fi

# 构建测试 Docker 镜像
echo "正在构建测试镜像 ${IMAGE_NAME}:${VERSION} ..."
docker build -t ${IMAGE_NAME}:latest -t ${IMAGE_NAME}:${VERSION} -f Dockerfile.test .

# 在容器中运行测试
echo "正在 Docker 容器中运行测试 (${IMAGE_NAME}:latest)..."
docker run --rm --network host -e TEST_PROJECT_ID="$TEST_PROJECT_ID" ${IMAGE_NAME}:latest
