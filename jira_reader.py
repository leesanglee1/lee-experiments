import subprocess
import json
import os
import requests
import logging
from vector_db_handler import create_vector_db_collection, upsert_vectors

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Configuration ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
MCP_SERVER_PATH = os.environ.get(
    "MCP_SERVER_PATH", "/home/codespace/Documents/Cline/MCP/jira-server/build/index.js"
)
JIRA_DOMAIN = os.environ.get("JIRA_DOMAIN")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN")
JIRA_PROJECT_KEY_DEFAULT = "PRTFL" # Default project key if not set in environment

# --- Helper Functions ---

def _validate_env_vars():
    """Validates that required environment variables are set."""
    required_vars = {
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "JIRA_DOMAIN": JIRA_DOMAIN,
        "JIRA_EMAIL": JIRA_EMAIL,
        "JIRA_API_TOKEN": JIRA_API_TOKEN,
    }
    missing_vars = [name for name, value in required_vars.items() if not value]
    if missing_vars:
        logger.error(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )
        return False
    return True


def run_mcp_command(tool_name: str, arguments: dict) -> dict | None:
    """
    Runs an MCP command via a Node.js script.

    Args:
        tool_name: The name of the MCP tool to call.
        arguments: A dictionary of arguments for the MCP tool.

    Returns:
        The JSON response from the MCP server as a dictionary, or None on error.
    """
    if not os.path.exists(MCP_SERVER_PATH):
        logger.error(f"MCP server script not found at: {MCP_SERVER_PATH}")
        return None

    current_env = os.environ.copy()
    if JIRA_DOMAIN:
        current_env["JIRA_DOMAIN"] = JIRA_DOMAIN
    if JIRA_EMAIL:
        current_env["JIRA_EMAIL"] = JIRA_EMAIL
    if JIRA_API_TOKEN:
        current_env["JIRA_API_TOKEN"] = JIRA_API_TOKEN

    command_payload = {
        "jsonrpc": "2.0",
        "method": "call_tool",
        "params": {"name": tool_name, "arguments": arguments},
        "id": 1,
    }
    command = ["node", MCP_SERVER_PATH, json.dumps(command_payload)]

    try:
        logger.info(f"Running MCP command: {tool_name} with args: {arguments}")
        result = subprocess.run(
            command, env=current_env, capture_output=True, text=True, check=True
        )
        logger.debug(f"MCP command stdout: {result.stdout}")
        logger.debug(f"MCP command stderr: {result.stderr}")
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(
            f"MCP command '{tool_name}' failed. Return code: {e.returncode}\n"
            f"Stdout: {e.stdout}\nStderr: {e.stderr}"
        )
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON response from MCP command '{tool_name}': {e}")
        logger.error(f"Non-JSON response: {result.stdout if 'result' in locals() else 'N/A'}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while running MCP command '{tool_name}': {e}")
    return None


def get_project_issues(
    project_key: str, max_results: int = 50, jql_filter: str = ""
) -> dict | None:
    """
    Retrieves issues for a given Jira project key.

    Args:
        project_key: The Jira project key (e.g., "PRTFL").
        max_results: The maximum number of issues to retrieve.
        jql_filter: An optional JQL filter string.

    Returns:
        A dictionary containing the issues, or None on error.
    """
    logger.info(
        f"Fetching issues for project '{project_key}' (max: {max_results}, jql: '{jql_filter or 'None'}')"
    )
    response = run_mcp_command(
        "get_project_issues",
        {
            "project_key": project_key,
            "max_results": max_results,
            "jql_filter": jql_filter,
        },
    )
    if response and response.get("result", {}).get("content"):
        try:
            # Assuming the actual issue data is in the first 'text' field of 'content'
            issues_data = json.loads(response["result"]["content"][0]["text"])
            logger.info(f"Successfully retrieved {len(issues_data.get('issues', []))} issues for project '{project_key}'.")
            return issues_data
        except (json.JSONDecodeError, IndexError, KeyError) as e:
            logger.error(f"Error parsing issues from MCP response for project '{project_key}': {e}")
            logger.debug(f"MCP Response causing parsing error: {response}")
            return None
    else:
        logger.warning(f"No issues found or error fetching issues for project '{project_key}'. Response: {response}")
        return None


def get_issue(issue_key: str) -> dict | None:
    """
    Retrieves details for a specific Jira issue.

    Args:
        issue_key: The Jira issue key (e.g., "PRTFL-123").

    Returns:
        A dictionary containing the issue details, or None on error.
    """
    logger.info(f"Fetching details for issue '{issue_key}'")
    response = run_mcp_command("get_issue", {"issue_key": issue_key})
    if response and response.get("result", {}).get("content"):
        try:
            issue_data = json.loads(response["result"]["content"][0]["text"])
            logger.info(f"Successfully retrieved details for issue '{issue_key}'.")
            return issue_data
        except (json.JSONDecodeError, IndexError, KeyError) as e:
            logger.error(f"Error parsing issue details from MCP response for '{issue_key}': {e}")
            logger.debug(f"MCP Response causing parsing error: {response}")
            return None
    else:
        logger.warning(f"No details found or error fetching issue '{issue_key}'. Response: {response}")
        return None


def get_text_embedding(text: str, model: str = "text-embedding-ada-002") -> list[float] | None:
    """
    Generates a text embedding using the OpenAI API.

    Args:
        text: The input text to embed.
        model: The OpenAI embedding model to use.

    Returns:
        A list of floats representing the embedding, or None on error.
    """
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not set. Cannot generate text embeddings.")
        return None
    if not text:
        logger.warning("Attempted to get embedding for empty text.")
        return None

    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }
    data = {"input": text, "model": model}

    try:
        logger.info(f"Requesting text embedding for text (length: {len(text)}) using model '{model}'.")
        response = requests.post(url, headers=headers, json=data, timeout=30) # Added timeout
        response.raise_for_status()  # Raises HTTPError for bad responses (4XX or 5XX)
        embedding_data = response.json()
        if embedding_data.get("data") and embedding_data["data"][0].get("embedding"):
            logger.info("Successfully generated text embedding.")
            return embedding_data["data"][0]["embedding"]
        else:
            logger.error(f"Unexpected response structure from OpenAI API: {embedding_data}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"OpenAI API request failed: {e}")
    except (KeyError, IndexError) as e:
        logger.error(f"Error parsing OpenAI API response: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during text embedding: {e}")
    return None


def vectorize_jira_issue(issue: dict) -> dict | None:
    """
    Vectorizes a Jira issue by combining its summary and description.

    Args:
        issue: A dictionary representing a Jira issue.

    Returns:
        A dictionary with the issue ID, vector, and metadata, or None on error.
    """
    try:
        issue_key = issue["key"]
        summary = issue.get("fields", {}).get("summary", "")
        description = issue.get("fields", {}).get("description") or "" # Handles None description
        
        if not summary and not description:
            logger.warning(f"Issue {issue_key} has no summary or description. Skipping vectorization.")
            return None

        combined_text = f"Summary: {summary}\n\nDescription: {description}".strip()
        logger.info(f"Vectorizing issue '{issue_key}'. Combined text length: {len(combined_text)}")

        vector = get_text_embedding(combined_text)
        if vector:
            vectorized_data = {
                "id": issue_key,
                "values": vector,
                "metadata": {"summary": summary, "description": description, "project": issue.get("fields", {}).get("project", {}).get("key")},
            }
            logger.info(f"Successfully vectorized issue '{issue_key}'.")
            return vectorized_data
        else:
            logger.error(f"Failed to get embedding for issue '{issue_key}'.")
            return None
    except KeyError as e:
        logger.error(f"Missing expected key in issue data for vectorization: {e}. Issue  {issue}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during vectorization of issue: {e}")
        return None

# --- Main Execution ---

def main():
    """
    Main function to fetch, vectorize, and store Jira issues.
    """
    if not _validate_env_vars():
        logger.error("Exiting due to missing environment variables.")
        return

    project_key_to_use = os.environ.get("JIRA_PROJECT_KEY", JIRA_PROJECT_KEY_DEFAULT)
    collection_name = f"jira_issues_{project_key_to_use.lower().replace('-', '_')}" # Dynamic collection name

    logger.info(f"Starting Jira issue processing for project: {project_key_to_use}")
    logger.info(f"Vector DB collection name: {collection_name}")

    # 1. Create vector database collection (idempotent)
    try:
        create_vector_db_collection(collection_name)
        logger.info(f"Ensured vector DB collection '{collection_name}' exists.")
    except Exception as e:
        logger.error(f"Failed to create/ensure vector DB collection '{collection_name}': {e}")
        return # Stop if DB setup fails

    # 2. Get Jira issues
    # Consider adding pagination or more robust fetching for many issues
    issues_data = get_project_issues(project_key_to_use, max_results=10) # Keep max_results low for example

    if not issues_data or not issues_data.get("issues"):
        logger.warning(f"No issues retrieved for project '{project_key_to_use}'. Exiting.")
        return

    logger.info(f"Retrieved {len(issues_data['issues'])} issues for project '{project_key_to_use}'.")
    for issue in issues_data["issues"]:
        logger.info(f"  - {issue.get('key')}: {issue.get('fields', {}).get('summary', 'No summary')}")

    # 3. Vectorize and store Jira issues
    vectorized_issues_list = []
    for issue in issues_data["issues"]:
        vectorized = vectorize_jira_issue(issue)
        if vectorized:
            vectorized_issues_list.append(vectorized)
    
    if not vectorized_issues_list:
        logger.warning("No issues were successfully vectorized. Nothing to upsert.")
    else:
        try:
            logger.info(f"Upserting {len(vectorized_issues_list)} vectorized issues into '{collection_name}'.")
            upsert_result = upsert_vectors(collection_name, vectorized_issues_list)
            logger.info(f"Vector upsert result: {upsert_result}")
        except Exception as e:
            logger.error(f"Failed to upsert vectors into '{collection_name}': {e}")


    # 4. Get details of a specific issue (example: first retrieved issue)
    if issues_data["issues"]:
        first_issue_key = issues_data["issues"][0].get("key")
        if first_issue_key:
            logger.info(f"Fetching details for example issue: {first_issue_key}")
            issue_details = get_issue(first_issue_key)
            if issue_details:
                logger.info(
                    f"Details of issue {first_issue_key}:\n{json.dumps(issue_details, indent=2)}"
                )
            else:
                logger.warning(f"Could not retrieve details for example issue {first_issue_key}.")
        else:
            logger.warning("First issue in the list has no key.")
    
    logger.info("Jira issue processing finished.")


if __name__ == "__main__":
    main()
