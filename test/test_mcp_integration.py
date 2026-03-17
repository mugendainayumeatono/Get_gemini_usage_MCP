import os
import pytest
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8000/sse")

@pytest.mark.asyncio
async def test_mcp_server_connection_and_tools():
    try:
        print("\n--- [集成测试] 开始连接 MCP 服务器 ---")
        async with sse_client(MCP_SERVER_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print(">>> 成功初始化会话。")
                
                tools_response = await session.list_tools()
                tool_names = [tool.name for tool in tools_response.tools]
                print(f">>> 成功获取工具列表: {tool_names}")
                
                assert "list_token_metrics" in tool_names
                assert "get_monthly_metric_sum" in tool_names
                assert "get_metric_sum_for_time_range" in tool_names
                assert "query_billing_token_usage_from_bigquery" in tool_names
                
                print("\n--- [集成测试] 测试调用 list_token_metrics ---")
                project_id = os.environ.get("TEST_PROJECT_ID", "fake-project")
                print(f">>> 正在发送请求，参数: project_id='{project_id}'")
                
                result = await session.call_tool("list_token_metrics", arguments={"project_id": project_id})
                assert result is not None
                
                assert len(result.content) > 0
                assert result.content[0].type == "text"
                
                response_text = result.content[0].text
                print(f"\n========== MCP 服务器返回结果 ==========\n{response_text}\n======================================\n")
                
                assert "Error listing metrics:" not in response_text
                print(">>> 测试通过: 成功获取了服务器返回的内容，且没有出现指标列举错误。")
    except Exception as e:
        pytest.fail(f"Failed to connect to MCP server or call tools: {e}")

@pytest.mark.asyncio
async def test_mcp_get_monthly_metric_sum_flow():
    """
    Integration test for the flow: 
    1. list_token_metrics -> Get metric types
    2. get_monthly_metric_sum -> Get value for each metric type
    """
    try:
        print("\n--- [集成测试] 开始测试获取月度指标总和流程 ---")
        async with sse_client(MCP_SERVER_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                project_id = os.environ.get("TEST_PROJECT_ID", "fake-project")
                
                # 1. List metrics
                print(">>> 步骤1: 调用 list_token_metrics 获取指标列表")
                list_result = await session.call_tool("list_token_metrics", arguments={"project_id": project_id})
                list_text = list_result.content[0].text
                
                if "Found metrics:" not in list_text:
                    print(f">>> 未发现相关指标: {list_text}")
                    return

                # Parse metric types
                lines = list_text.strip().split("\n")
                metric_types = lines[1:]
                print(f">>> 发现 {len(metric_types)} 个指标类型，将全部进行测试。")
                
                # 2. Get monthly sum for each metric
                for metric_type in metric_types:
                    print(f">>> 步骤2: 调用 get_monthly_metric_sum, 参数: metric_type='{metric_type}'")
                    sum_result = await session.call_tool("get_monthly_metric_sum", 
                                                       arguments={"project_id": project_id, "metric_type": metric_type})
                    sum_text = sum_result.content[0].text
                    print(f"    结果: {sum_text}")
                    
                    assert f"Total for {metric_type}" in sum_text
                    assert "Error" not in sum_text

                print(">>> 测试通过: 完整指标查询流程成功执行。")
    except Exception as e:
        pytest.fail(f"Integrated flow test failed: {e}")

@pytest.mark.asyncio
async def test_mcp_get_metric_sum_for_time_range_flow():
    """
    Integration test for the flow: 
    1. list_token_metrics -> Get metric types
    2. get_metric_sum_for_time_range -> Get value from a specific time range
    """
    try:
        print("\n--- [集成测试] 开始测试自定义时间范围获取指标总和流程 ---")
        async with sse_client(MCP_SERVER_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                project_id = os.environ.get("TEST_PROJECT_ID", "fake-project")
                
                # 1. List metrics
                print(">>> 步骤1: 调用 list_token_metrics 获取指标列表")
                list_result = await session.call_tool("list_token_metrics", arguments={"project_id": project_id})
                list_text = list_result.content[0].text
                
                if "Found metrics:" not in list_text:
                    print(f">>> 未发现相关指标: {list_text}")
                    return

                # Parse metric types
                lines = list_text.strip().split("\n")
                metric_types = lines[1:]
                print(f">>> 发现 {len(metric_types)} 个指标类型。")
                
                if not metric_types:
                    return

                # Just test the first metric to save time
                metric_type = metric_types[0]
                import datetime
                end_time = datetime.datetime.now(datetime.timezone.utc)
                start_time = end_time - datetime.timedelta(days=1)
                
                start_time_str = start_time.strftime("%Y-%m-%d_%H:%M:%S")
                end_time_str = end_time.strftime("%Y-%m-%d_%H:%M:%S")
                
                print(f">>> 步骤2: 调用 get_metric_sum_for_time_range, 参数: metric_type='{metric_type}', start_time_str='{start_time_str}', end_time_str='{end_time_str}'")
                sum_result = await session.call_tool("get_metric_sum_for_time_range", 
                                                   arguments={"project_id": project_id, "metric_type": metric_type, "start_time_str": start_time_str, "end_time_str": end_time_str})
                sum_text = sum_result.content[0].text
                print(f"    结果: {sum_text}")
                
                assert f"Total for {metric_type} between {start_time_str} and {end_time_str}" in sum_text
                assert "Error" not in sum_text

                print(">>> 测试通过: 自定义时间指标查询流程成功执行。")
    except Exception as e:
        pytest.fail(f"Integrated flow test failed: {e}")
