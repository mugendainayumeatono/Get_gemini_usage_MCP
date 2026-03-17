import pytest
from unittest.mock import patch, MagicMock
import datetime
import sys
import os

# Add the parent directory to sys.path to import mcp_server
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mcp_server import list_token_metrics, get_monthly_metric_sum, get_metric_sum_for_time_range, query_billing_token_usage_from_bigquery

@patch('mcp_server.monitoring_v3')
def test_list_token_metrics_success(mock_monitoring_v3):

    # Setup mock
    mock_client = MagicMock()
    mock_monitoring_v3.MetricServiceClient.return_value = mock_client
    
    mock_result_1 = MagicMock()
    mock_result_1.type = "generativelanguage.googleapis.com/quota/generate_content_free_tier_input_token_count/usage"
    mock_result_2 = MagicMock()
    mock_result_2.type = "generativelanguage.googleapis.com/quota/generate_content_paid_tier_input_token_count/usage"
    
    mock_client.list_metric_descriptors.return_value = [mock_result_1, mock_result_2]

    # Call the function
    result = list_token_metrics("test-project-id")

    # Assertions
    assert "Found metrics:" in result
    assert "generativelanguage.googleapis.com/quota/generate_content_free_tier_input_token_count/usage" in result
    assert "generativelanguage.googleapis.com/quota/generate_content_paid_tier_input_token_count/usage" in result
    mock_client.list_metric_descriptors.assert_called_once()
    
@patch('mcp_server.monitoring_v3')
def test_list_token_metrics_no_results(mock_monitoring_v3):
    mock_client = MagicMock()
    mock_monitoring_v3.MetricServiceClient.return_value = mock_client
    mock_client.list_metric_descriptors.return_value = []

    result = list_token_metrics("test-project-id")

    assert "No metrics found starting with 'generativelanguage.googleapis.com/quota/generate'" in result
    
@patch('mcp_server.monitoring_v3')
def test_list_token_metrics_error(mock_monitoring_v3):
    mock_client = MagicMock()
    mock_monitoring_v3.MetricServiceClient.return_value = mock_client
    mock_client.list_metric_descriptors.side_effect = Exception("API Error")

    result = list_token_metrics("test-project-id")

    assert "Error listing metrics: API Error" in result


@patch('mcp_server.monitoring_v3')
def test_get_monthly_metric_sum_success(mock_monitoring_v3):
    mock_client = MagicMock()
    mock_monitoring_v3.MetricServiceClient.return_value = mock_client
    
    mock_point_1 = MagicMock()
    mock_point_1.value.int64_value = 100
    mock_point_2 = MagicMock()
    mock_point_2.value.int64_value = 150
    
    mock_result = MagicMock()
    mock_result.points = [mock_point_1, mock_point_2]
    
    mock_client.list_time_series.return_value = [mock_result]

    result = get_monthly_metric_sum("test-project", "test.metric/token")

    assert "Total for test.metric/token this month: 250" in result
    mock_client.list_time_series.assert_called_once()

@patch('mcp_server.monitoring_v3')
def test_get_monthly_metric_sum_error(mock_monitoring_v3):
    mock_client = MagicMock()
    mock_monitoring_v3.MetricServiceClient.return_value = mock_client
    mock_client.list_time_series.side_effect = Exception("API Error")

    result = get_monthly_metric_sum("test-project", "test.metric/token")

    assert "Error querying metric: API Error" in result

@patch('mcp_server.monitoring_v3')
def test_get_metric_sum_for_time_range_success(mock_monitoring_v3):
    mock_client = MagicMock()
    mock_monitoring_v3.MetricServiceClient.return_value = mock_client
    
    mock_point_1 = MagicMock()
    mock_point_1.value.int64_value = 100
    mock_point_2 = MagicMock()
    mock_point_2.value.int64_value = 150
    
    mock_result = MagicMock()
    mock_result.points = [mock_point_1, mock_point_2]
    
    mock_client.list_time_series.return_value = [mock_result]

    result = get_metric_sum_for_time_range("test-project", "test.metric/token", "2023-01-01_12:00:00", "2023-01-02_12:00:00")

    assert "Total for test.metric/token between 2023-01-01_12:00:00 and 2023-01-02_12:00:00: 250" in result
    mock_client.list_time_series.assert_called_once()

@patch('mcp_server.monitoring_v3')
def test_get_metric_sum_for_time_range_invalid_format(mock_monitoring_v3):
    result = get_metric_sum_for_time_range("test-project", "test.metric/token", "2023/01/01", "2023-01-02_12:00:00")
    assert "Error querying metric: Invalid time format" in result

@patch('mcp_server.monitoring_v3')
def test_get_metric_sum_for_time_range_future_date(mock_monitoring_v3):
    # Create a future date strictly greater than now
    now_date = datetime.datetime.now(datetime.timezone.utc)
    future_date = (now_date + datetime.timedelta(days=1)).strftime("%Y-%m-%d_%H:%M:%S")
    past_date = (now_date - datetime.timedelta(days=1)).strftime("%Y-%m-%d_%H:%M:%S")
    result = get_metric_sum_for_time_range("test-project", "test.metric/token", past_date, future_date)
    assert "Error querying metric: End time cannot be in the future" in result

@patch('mcp_server.monitoring_v3')
def test_get_metric_sum_for_time_range_start_after_end(mock_monitoring_v3):
    result = get_metric_sum_for_time_range("test-project", "test.metric/token", "2023-01-02_12:00:00", "2023-01-01_12:00:00")
    assert "Error querying metric: Start time cannot be after end time" in result

@patch('mcp_server.bigquery.Client')
def test_query_billing_token_usage_from_bigquery_success(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_query_job = MagicMock()
    
    mock_row_1 = MagicMock()
    mock_row_1.description = "Vertex AI Gemini 1.5 Pro Input"
    mock_row_1.total_usage = 50000
    mock_row_1.unit = "tokens"
    
    mock_query_job.result.return_value = [mock_row_1]
    mock_client.query.return_value = mock_query_job

    result = query_billing_token_usage_from_bigquery("test-project", "project.dataset.table")

    assert "SKU: Vertex AI Gemini 1.5 Pro Input | Usage: 50000 tokens" in result
    mock_client.query.assert_called_once()

@patch('mcp_server.bigquery.Client')
def test_query_billing_token_usage_from_bigquery_no_results(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_query_job = MagicMock()
    mock_query_job.result.return_value = []
    mock_client.query.return_value = mock_query_job

    result = query_billing_token_usage_from_bigquery("test-project", "project.dataset.table")

    assert "No token usage found in billing data for this month." in result

@patch('mcp_server.bigquery.Client')
def test_query_billing_token_usage_from_bigquery_error(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.query.side_effect = Exception("BQ API Error")

    result = query_billing_token_usage_from_bigquery("test-project", "project.dataset.table")

    assert "Error querying BigQuery: BQ API Error" in result

@patch('mcp_server.monitoring_v3')
def test_get_monthly_metric_sum_with_list_token_metrics(mock_monitoring_v3):
    mock_client = MagicMock()
    mock_monitoring_v3.MetricServiceClient.return_value = mock_client
    
    # Setup mock for list_metric_descriptors
    mock_result_1 = MagicMock()
    mock_result_1.type = "generativelanguage.googleapis.com/quota/generate_content_free_tier_input_token_count/usage"
    mock_result_2 = MagicMock()
    mock_result_2.type = "generativelanguage.googleapis.com/quota/generate_content_paid_tier_input_token_count/usage"
    mock_client.list_metric_descriptors.return_value = [mock_result_1, mock_result_2]

    # Setup mock for list_time_series
    mock_point_1 = MagicMock()
    mock_point_1.value.int64_value = 100
    mock_point_2 = MagicMock()
    mock_point_2.value.int64_value = 150
    mock_result = MagicMock()
    mock_result.points = [mock_point_1, mock_point_2]
    mock_client.list_time_series.return_value = [mock_result]

    # 1. Get metric_types using list_token_metrics
    list_result = list_token_metrics("test-project-id")
    
    # Parse the metrics from the result string
    lines = list_result.strip().split("\n")
    assert lines[0] == "Found metrics:"
    metric_types = lines[1:]
    
    assert len(metric_types) == 2
    
    # 2. Get monthly sum for each metric_type
    monthly_sums = []
    for metric_type in metric_types:
        monthly_sums.append(get_monthly_metric_sum("test-project-id", metric_type))
        
    # Assertions
    assert "Total for generativelanguage.googleapis.com/quota/generate_content_free_tier_input_token_count/usage this month: 250" in monthly_sums[0]
    assert "Total for generativelanguage.googleapis.com/quota/generate_content_paid_tier_input_token_count/usage this month: 250" in monthly_sums[1]
    
    mock_client.list_metric_descriptors.assert_called_once()
    assert mock_client.list_time_series.call_count == 2
