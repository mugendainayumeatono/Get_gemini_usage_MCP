# AI Agent Instructions: Google Cloud Token Usage MCP

Use the following instructions to understand how to utilize the "Google Token Usage" MCP server capabilities effectively.

## Service Overview
This MCP server provides tools to query Google Cloud Platform (GCP) for token usage data, specifically focusing on Large Language Models (LLMs) like Gemini and Vertex AI. It bridges the gap between raw cloud metrics/billing data and user questions about consumption.

## Tool Definitions & Usage Strategy

### 1. `query_billing_token_usage_from_bigquery`
*   **Description**: Queries the official Google Cloud Billing export table in BigQuery.
*   **Best For**: Accurate, billing-aligned token counts. This is the **preferred method** if the user has Billing Export enabled.
*   **Parameters**:
    *   `project_id` (string): The GCP Project ID.
    *   `table_id` (string): The full BigQuery table ID containing billing data (e.g., `my-project.billing_dataset.gcp_billing_export_v1_XXXXXX`).
*   **Strategy**:
    *   Ask the user if they have "Cloud Billing Export to BigQuery" enabled.
    *   If yes, ask for the `table_id` and use this tool. (The `table_id` can be found in the Cloud Console under Billing -> Billing export).
    *   It returns a breakdown of usage by SKU (e.g., "Input Tokens", "Output Tokens").

### 2. `list_token_metrics`
*   **Description**: Searches the Google Cloud Monitoring API specifically for metrics starting with `generativelanguage.googleapis.com/quota/generate`.
*   **Best For**: Discovery. Use this to find the exact metric names for Gemini API quota and usage (e.g., free tier vs. paid tier input/output token usage).
*   **Parameters**:
    *   `project_id` (string): The GCP Project ID.
*   **Strategy**:
    *   Use this first if the user relies on Cloud Monitoring (not Billing Export) to find the exact metric URI needed for subsequent queries.

### 3. `get_monthly_metric_sum`
*   **Description**: Aggregates the sum of a specific metric from the 1st of the current month to the current moment.
*   **Best For**: Getting a "Month-to-Date" total for a specific technical metric found via `list_token_metrics`.
*   **Parameters**:
    *   `project_id` (string): The GCP Project ID.
    *   `metric_type` (string): The exact metric URI (e.g., `generativelanguage.googleapis.com/quota/generate_content_paid_tier_input_token_count/usage`).
*   **Strategy**:
    *   Call this *after* obtaining a valid `metric_type` from `list_token_metrics` when the user wants to know their usage for the current month.

### 4. `get_metric_sum_for_time_range`
*   **Description**: Aggregates the sum of a specific metric within a custom, user-defined time range.
*   **Best For**: Getting token usage for specific days, weeks, or past months.
*   **Parameters**:
    *   `project_id` (string): The GCP Project ID.
    *   `metric_type` (string): The exact metric URI.
    *   `start_time_str` (string): The start time in `YYYY-MM-DD_HH:MM:SS` (UTC) format.
    *   `end_time_str` (string): The end time in `YYYY-MM-DD_HH:MM:SS` (UTC) format.
*   **Strategy**:
    *   Use this when the user asks for usage "yesterday", "last week", or between specific dates. Ensure you format the dates correctly before calling the tool.

## Standard Operating Procedure (SOP) for AI

1.  **Context Gathering**:
    *   Always ensure you have the `project_id`. If not provided, ask the user: "Which Google Cloud Project ID should I check?"
    *   Determine the time range the user is interested in (This Month vs. Custom Range).
    *   Determine the data source preference: "Do you want to check via Cloud Monitoring metrics (approximate) or BigQuery Billing Export (precise)?"

2.  **Scenario A: Billing/Cost Focus (Preferred)**
    *   If the user mentions "cost", "bill", or "precise usage", attempt to use `query_billing_token_usage_from_bigquery`.
    *   *Requirement*: You need the BigQuery `table_id`.

3.  **Scenario B: Technical/Monitoring Focus**
    *   If the user just wants a quick technical check or doesn't have BigQuery export.
    *   Step 1: Call `list_token_metrics(project_id="...")`.
    *   Step 2: Analyze the list. Look for `usage` metrics related to `free_tier` or `paid_tier` token counts.
    *   Step 3: Based on the requested time frame, call either `get_monthly_metric_sum` (for this month) or `get_metric_sum_for_time_range` (for custom dates).
    *   Step 4: Report the total to the user, noting that this is "monitoring data" and might differ slightly from the final bill.

## Example Interaction

**User**: "How many paid Gemini input tokens did I use yesterday in project 'my-ai-app'?"

**AI Thought Process**:
1.  I have the project ID: `my-ai-app`.
2.  The time range is "yesterday" (Custom range).
3.  First, I need to see what token metrics exist to find the exact name for paid input tokens.

**Tool Call**: `list_token_metrics(project_id="my-ai-app")`

**Tool Output**:
```text
Found metrics:
generativelanguage.googleapis.com/quota/generate_content_paid_tier_input_token_count/limit
generativelanguage.googleapis.com/quota/generate_content_paid_tier_input_token_count/usage
...
```

**AI Thought Process**:
1.  I found the metric: `generativelanguage.googleapis.com/quota/generate_content_paid_tier_input_token_count/usage`.
2.  Now I will sum it up for yesterday's date range (e.g., 2024-03-15).

**Tool Call**: `get_metric_sum_for_time_range(project_id="my-ai-app", metric_type="generativelanguage.googleapis.com/quota/generate_content_paid_tier_input_token_count/usage", start_time_str="2024-03-15_00:00:00", end_time_str="2024-03-16_00:00:00")`

**Tool Output**: `Total for ... between 2024-03-15_00:00:00 and 2024-03-16_00:00:00: 4500`

**AI Response**: "According to Cloud Monitoring, project 'my-ai-app' consumed approximately **4,500 paid input tokens** yesterday."
