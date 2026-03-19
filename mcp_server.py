from fastmcp import FastMCP
from google.cloud import monitoring_v3
from google.cloud import bigquery
from google.protobuf.timestamp_pb2 import Timestamp
import datetime
import logging

import sys
import os

# Initialize FastMCP server
mcp = FastMCP("google-token-usage")

def debug_credentials():
    print("\n--- DEBUG INFO ---", file=sys.stderr)
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    print(f"GOOGLE_APPLICATION_CREDENTIALS: {creds_path}", file=sys.stderr)
    
    if creds_path:
        if os.path.exists(creds_path):
            print(f"File exists at path: Yes", file=sys.stderr)
            try:
                with open(creds_path, 'r') as f:
                    print("File content:", file=sys.stderr)
                    print(f.read(), file=sys.stderr)
            except Exception as e:
                print(f"Error reading file: {e}", file=sys.stderr)
        else:
            print(f"File exists at path: No", file=sys.stderr)
    else:
        print("GOOGLE_APPLICATION_CREDENTIALS is NOT set.", file=sys.stderr)
    print("------------------\n", file=sys.stderr)

@mcp.tool()
def list_token_metrics(project_id: str) -> str:
    """
    Lists available metrics in Google Cloud Monitoring that start with 
    'generativelanguage.googleapis.com/quota/generate'.
    Useful for finding Gemini API quota and usage metrics.
    """
    try:
        client = monitoring_v3.MetricServiceClient()
        project_name = f"projects/{project_id}"
        
        # Filter for specific generativelanguage quota metrics
        filter_str = 'metric.type = starts_with("generativelanguage.googleapis.com/quota/generate")'
        results = client.list_metric_descriptors(
            request={
                "name": project_name,
                "filter": filter_str,
            }
        )
        
        metrics = []
        for result in results:
            metrics.append(result.type)
            
        if not metrics:
            return "No metrics found starting with 'generativelanguage.googleapis.com/quota/generate'."
            
        return "Found metrics:\n" + "\n".join(metrics)
    except Exception as e:
        return f"Error listing metrics: {str(e)}"

@mcp.tool()
def get_monthly_metric_sum(project_id: str, metric_type: str) -> str:
    """
    Calculates the sum of a specific metric for the current month (from the 1st to now).
    Use this to get the total token count if you know the metric name (e.g., found via list_token_metrics).
    """
    try:
        client = monitoring_v3.MetricServiceClient()
        project_name = f"projects/{project_id}"

        now = datetime.datetime.now(datetime.timezone.utc)
        first_day = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        start_timestamp = Timestamp()
        start_timestamp.seconds = int(first_day.timestamp())
        end_timestamp = Timestamp()
        end_timestamp.seconds = int(now.timestamp())
        
        interval = monitoring_v3.TimeInterval(
            start_time=start_timestamp,
            end_time=end_timestamp
        )

        # Aggregation settings: Sum over the time period
        alignment_period_seconds = int((now - first_day).total_seconds())
        if alignment_period_seconds < 1:
            alignment_period_seconds = 1
            
        aggregation = monitoring_v3.Aggregation(
            alignment_period={"seconds": alignment_period_seconds},
            per_series_aligner=monitoring_v3.Aggregation.Aligner.ALIGN_SUM,
            cross_series_reducer=monitoring_v3.Aggregation.Reducer.REDUCE_SUM
        )

        results = client.list_time_series(
            request={
                "name": project_name,
                "filter": f'metric.type = "{metric_type}"',
                "interval": interval,
                "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                "aggregation": aggregation
            }
        )

        total_val = 0
        for result in results:
            for point in result.points:
                # Assuming int64 value for counts
                total_val += point.value.int64_value

        return f"Total for {metric_type} this month: {total_val}"

    except Exception as e:
        return f"Error querying metric: {str(e)}"

@mcp.tool()
def get_metric_sum_for_time_range(project_id: str, metric_type: str, start_time_str: str, end_time_str: str) -> str:
    """
    Calculates the sum of a specific metric from a specified start time to a specified end time.
    Time format must be 'YYYY-MM-DD_HH:MM:SS' (UTC).
    Use this to get the total token count for a custom time range.
    """
    try:
        client = monitoring_v3.MetricServiceClient()
        project_name = f"projects/{project_id}"

        now = datetime.datetime.now(datetime.timezone.utc)
        
        try:
            start_time = datetime.datetime.strptime(start_time_str, "%Y-%m-%d_%H:%M:%S").replace(tzinfo=datetime.timezone.utc)
            end_time = datetime.datetime.strptime(end_time_str, "%Y-%m-%d_%H:%M:%S").replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            return "Error querying metric: Invalid time format. Please use 'YYYY-MM-DD_HH:MM:SS'."

        if start_time > end_time:
            return "Error querying metric: Start time cannot be after end time."
            
        if end_time > now:
            return "Error querying metric: End time cannot be in the future."
        
        start_timestamp = Timestamp()
        start_timestamp.seconds = int(start_time.timestamp())
        end_timestamp = Timestamp()
        end_timestamp.seconds = int(end_time.timestamp())
        
        interval = monitoring_v3.TimeInterval(
            start_time=start_timestamp,
            end_time=end_timestamp
        )

        # Aggregation settings: Sum over the time period
        alignment_period_seconds = int((end_time - start_time).total_seconds())
        if alignment_period_seconds < 1:
            alignment_period_seconds = 1
            
        aggregation = monitoring_v3.Aggregation(
            alignment_period={"seconds": alignment_period_seconds},
            per_series_aligner=monitoring_v3.Aggregation.Aligner.ALIGN_SUM,
            cross_series_reducer=monitoring_v3.Aggregation.Reducer.REDUCE_SUM
        )

        results = client.list_time_series(
            request={
                "name": project_name,
                "filter": f'metric.type = "{metric_type}"',
                "interval": interval,
                "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                "aggregation": aggregation
            }
        )

        total_val = 0
        for result in results:
            for point in result.points:
                # Assuming int64 value for counts
                total_val += point.value.int64_value

        return f"Total for {metric_type} between {start_time_str} and {end_time_str}: {total_val}"

    except Exception as e:
        return f"Error querying metric: {str(e)}"

@mcp.tool()
def query_billing_token_usage_from_bigquery(project_id: str, table_id: str) -> str:
    """
    Queries Google Cloud Billing Export in BigQuery to get token usage for the current month.
    
    Args:
        project_id: The Google Cloud Project ID to filter usage for.
        table_id: The BigQuery table ID where billing data is exported. 
                  Format: `project-id.dataset_id.gcp_billing_export_v1_XXXXXX_XXXXXX_XXXXXX`
                  
    Note: Requires that you have set up Cloud Billing Export to BigQuery.
    """
    try:
        client = bigquery.Client()
        
        now = datetime.datetime.now(datetime.timezone.utc)
        first_day_str = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
        
        # Safe query construction using parameters is hard with table names, 
        # but bigquery python client handles params well for values.
        # We trust the user provided table_id is correct or it will error.
        
        query = f"""
            SELECT
                sku.description,
                SUM(usage.amount) as total_usage,
                usage.unit
            FROM
                `{table_id}`
            WHERE
                usage_start_time >= TIMESTAMP(@start_date)
                AND project.id = @project_id
                AND (LOWER(sku.description) LIKE "%token%" OR LOWER(usage.unit) LIKE "%token%")
            GROUP BY
                sku.description, usage.unit
            ORDER BY
                total_usage DESC
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start_date", "STRING", first_day_str),
                bigquery.ScalarQueryParameter("project_id", "STRING", project_id),
            ]
        )
        
        query_job = client.query(query, job_config=job_config)
        results = query_job.result()
        
        output = []
        for row in results:
            output.append(f"SKU: {row.description} | Usage: {row.total_usage} {row.unit}")
            
        if not output:
            return "No token usage found in billing data for this month."
            
        return "\n".join(output)

    except Exception as e:
        return f"Error querying BigQuery: {str(e)}\nHint: Ensure you have the 'BigQuery Data Viewer' and 'BigQuery Job User' roles, and the table ID is correct."

if __name__ == "__main__":
    if os.environ.get("MCP_DEBUG") == "true":
        debug_credentials()
    
    # Allow overriding transport via environment variable, default to streamable-http for network access
    transport = os.environ.get("FASTMCP_TRANSPORT", "streamable-http")
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    print(f"Starting MCP server with transport={transport}, host={host}, port={port}", file=sys.stderr)
    mcp.run(transport=transport, host=host, port=port)
