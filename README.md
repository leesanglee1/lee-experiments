# Jira Project Reader

This project provides a Python script that reads data from a Jira project using a custom MCP server.

## Setup

1. Install the MCP server dependencies:
```bash
cd /home/codespace/Documents/Cline/MCP/jira-server
npm install
npm run build
```

2. Configure your Jira credentials:
   - Get your Jira API token from https://id.atlassian.com/manage-profile/security/api-tokens
   - Edit `jira_reader.py` and replace these values:
     - `your-jira-domain` with your Jira domain (e.g., "mycompany" if your Jira URL is mycompany.atlassian.net)
     - `your-jira-email` with your Jira account email
     - `your-jira-api-token` with your Jira API token
     - `YOUR_PROJECT_KEY` with your Jira project key (e.g., "PROJ")

## Usage

The script provides two main functions:

1. `get_project_issues(project_key, max_results=50, jql_filter="")`
   - Gets a list of issues from a project
   - Parameters:
     - `project_key`: Your Jira project key
     - `max_results`: Maximum number of issues to return (default: 50)
     - `jql_filter`: Additional JQL filters (optional)

2. `get_issue(issue_key)`
   - Gets detailed information about a specific issue
   - Parameters:
     - `issue_key`: The Jira issue key (e.g., "PROJ-123")

Example usage:

```python
# Get issues from a project
issues = get_project_issues("PROJ", max_results=10)
for issue in issues["issues"]:
    print(f"- {issue['key']}: {issue['fields']['summary']}")

# Get details of a specific issue
issue_details = get_issue("PROJ-123")
print(json.dumps(issue_details, indent=2))
```

## Running the Example

After configuring your credentials, run:

```bash
python jira_reader.py
```

This will display a list of issues from your project and detailed information about the first issue.
