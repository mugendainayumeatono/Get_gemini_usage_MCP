# Google Token Usage MCP Server

这是一个 MCP (Model Context Protocol) 服务，用于通过 Google Cloud Monitoring API 查询当前月份的 Google Cloud 项目（如 Vertex AI/Gemini）的 Token 使用情况。

## 前置要求

1.  **Python 3.10+**
2.  **Google Cloud Project**: 需要一个启用了 Monitoring API 的 Google Cloud 项目。
3.  **Authentication**: 需要配置 Google Cloud 凭据 (Application Default Credentials)。

## 安装

1.  安装依赖:
    ```bash
    pip install -r requirements.txt
    ```

2.  认证:
    获取 Google Cloud 凭据 (Application Default Credentials, ADC) 有两种主要方式：

    **方式一：使用 gcloud CLI（推荐本地开发）**
    确保已安装 [Google Cloud CLI](https://cloud.google.com/sdk/docs/install)，然后运行：
    ```bash
    gcloud auth application-default login
    ```
    这将打开浏览器进行登录，并在默认路径（如 `~/.config/gcloud/application_default_credentials.json`）生成凭据文件。对于依赖环境默认凭据的程序，这样就足够了。

    **方式二：使用服务账号密钥 (Service Account Key)**
    如果你在服务器、容器环境运行，或者不想使用个人账号：
    1. 前往 Google Cloud Console 的 [服务账号页面](https://console.cloud.google.com/iam-admin/serviceaccounts)。
    2. 创建或选择一个服务账号，确保其具有相关权限（如 `Monitoring Viewer`、`BigQuery Data Viewer` 和 `BigQuery Job User` 等）。
    3. 进入服务账号详情，点击“密钥”选项卡 -> “添加密钥” -> “创建新密钥” -> 选择 “JSON” 格式。
    4. 下载生成的 JSON 文件到本地。
    5. 设置 `GOOGLE_APPLICATION_CREDENTIALS` 环境变量指向该 JSON 文件的绝对路径：
       ```bash
       export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-file.json"
       ```

## 使用方法

### 方式一：Docker 运行 (推荐)

项目提供了一个便捷的脚本来构建并运行 Docker 容器。脚本会自动将本地的凭据挂载到容器内。此外，构建时会自动使用当前时间戳（例如 `v20240316-123000`）和 `latest` 标签标记镜像。

```bash
# 赋予脚本执行权限（仅需一次）
chmod +x run_docker.sh run_test_docker.sh

# 运行容器
./run_docker.sh

# 如果需要强制重新构建镜像，可以加上 -b 或 --build 参数
./run_docker.sh -b
```

**环境变量与凭据配置 (.env):**

建议在项目根目录下创建一个 `.env` 文件。脚本启动时会自动加载 `.env` 中的环境变量。
例如，要配置具体的 JSON 密钥文件路径，可以在 `.env` 中添加：
```ini
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-file.json
```
这样你无需修改任何脚本，就可以在不同凭据之间无缝切换。

**调试模式:**

如果你在启动或运行中遇到凭据相关问题，可以添加 `-d` 或 `--debug` 参数启动调试模式，这会输出相关的环境变量和挂载文件内容（通过向容器传递 `MCP_DEBUG=true`）：
```bash
./run_docker.sh --debug
```

### 方式二：直接运行 MCP 服务器

```bash
python mcp_server.py
```

### 可用工具 (Tools)

该服务暴露了以下工具:

1.  `list_token_metrics(project_id: str)`
    *   **描述**: 列出项目中所有名称包含 "token" 的 Cloud Monitoring 指标。
    *   **用途**: 用于查找具体的 Gemini 或 Vertex AI Token 计数指标名称（例如 `aiplatform.googleapis.com/.../token_count`）。

2.  `get_monthly_metric_sum(project_id: str, metric_type: str)`
    *   **描述**: 查询指定指标在**本月**（从1号到现在）的累加总和。
    *   **参数**:
        *   `project_id`: Google Cloud 项目 ID。
        *   `metric_type`: 指标类型名称。

3.  `get_metric_sum_for_time_range(project_id: str, metric_type: str, start_time_str: str, end_time_str: str)`
    *   **描述**: 查询指定指标在**指定的起始时间到结束时间**内的累加总和。
    *   **参数**:
        *   `project_id`: Google Cloud 项目 ID。
        *   `metric_type`: 指标类型名称。
        *   `start_time_str`: 起始时间字符串，格式必须为 `YYYY-MM-DD_HH:MM:SS` (UTC)。
        *   `end_time_str`: 结束时间字符串，格式必须为 `YYYY-MM-DD_HH:MM:SS` (UTC)。

4.  `query_billing_token_usage_from_bigquery(project_id: str, table_id: str)`
    *   **描述**: 通过 BigQuery 查询 Google Cloud Billing 导出数据，获取本月 Token 使用量。
    *   **参数**:
        *   `project_id`: 要查询的项目 ID。
        *   `table_id`: BigQuery 中的账单导出表 ID。格式为 `项目ID.数据集ID.表名`。
            *   **如何获取 Table ID**:
                1. 进入 Google Cloud Console 的 **Billing (结算)** -> **Billing export (账单导出)**。
                2. 确认已启用 BigQuery 导出，并记录配置的 **项目 ID** 和 **数据集 ID**。
                3. 进入 **BigQuery** 控制台，展开该项目和数据集。
                4. 找到名称类似于 `gcp_billing_export_v1_XXXXXX_XXXXXX_XXXXXX` 的表。
                5. 将这三部分组合，例如：`my-billing-project.billing_data.gcp_billing_export_v1_012345_6789AB_CDEF01`。
    *   **前置条件**: 您必须已在 Google Cloud Billing 中配置了导出到 BigQuery，并拥有 `BigQuery Data Viewer` 和 `BigQuery Job User` 权限。

## 常见指标参考

本工具主要获取 **`generativelanguage.googleapis.com`** 命名空间下的指标，用于监控 Gemini API 的使用情况。

获取的指标包含：
*   **免费层级 (Free Tier)**: 包含输入/输出 Token 计数。
*   **付费层级 (Paid Tier)**: 包含标准付费层级的输入/输出 Token 计数。
*   **付费层级细节 (Tiered Usage)**: 包含不同付费等级（如 Tier 1, Tier 2, Tier 3）的具体使用量和限制情况。

您可以通过 `list_token_metrics` 工具实时列出当前项目可用的所有具体指标路径。

**注意**: Cloud Monitoring API 提供的指标数据主要用于实时监控和配额查看，可能与最终的结算账单（Billing）存在微小差异。如需最精确的计费数据，请参考本工具提供的 BigQuery 账单查询功能。
