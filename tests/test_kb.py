import boto3
from app.core import settings

def test_knowledge_base(kb_id):
    try:
        bedrock_agent_runtime_client = boto3.client(
            'bedrock-agent-runtime',
            region_name=settings.BEDROCK_REGION
            )
        # Try to retrieve from the knowledge base
        response = bedrock_agent_runtime_client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": 1
                }
            },
            retrievalQuery={
                'text': 'test query'
            }
        )
        print(f"Knowledge Base {kb_id} exists and is accessible.")
        return True
    except Exception as e:
        print(f"Error accessing Knowledge Base {kb_id}: {str(e)}")
        return False

if __name__ == "__main__":
    kb_id = "OYWXI5HX47"  # Using the KB ID from the example
    test_knowledge_base(settings.KNOWLEDGE_BASE_ID)
