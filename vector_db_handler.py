import requests
import json
import os

VECTOR_DB_API_KEY = os.environ.get("VECTOR_DB_API_KEY")
VECTOR_DB_REGION = "us-east-1"  # Replace with your actual region
VECTOR_DB_NAMESPACE = "jira_tickets"  # Replace with your desired namespace

def create_vector_db_collection(collection_name):
    url = f"https://vectors.fuelix.ai/{VECTOR_DB_REGION}/v2/namespaces/{VECTOR_DB_NAMESPACE}"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {VECTOR_DB_API_KEY}"
    }
    
    data = {
        "name": collection_name,
        "dimension": 1536,  # Assuming we're using OpenAI's text-embedding-ada-002 model
        "metric": "cosine"
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

def upsert_vectors(collection_name, vectors):
    url = f"https://vectors.fuelix.ai/{VECTOR_DB_REGION}/v2/namespaces/{VECTOR_DB_NAMESPACE}/{collection_name}/upsert"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {VECTOR_DB_API_KEY}"
    }
    
    data = {
        "vectors": vectors
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

if __name__ == "__main__":
    # Example usage
    collection_name = "jira_tickets"
    create_result = create_vector_db_collection(collection_name)
    print(f"Collection creation result: {create_result}")

    # Example vector data (replace with actual vectorized Jira ticket data)
    example_vectors = [
        {
            "id": "JIRA-1",
            "values": [0.1, 0.2, 0.3],  # Replace with actual vector values
            "metadata": {
                "summary": "Example Jira ticket",
                "description": "This is an example Jira ticket"
            }
        }
    ]

    upsert_result = upsert_vectors(collection_name, example_vectors)
    print(f"Vector upsert result: {upsert_result}")
