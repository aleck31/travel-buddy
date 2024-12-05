# 参考以下代码，使用'bedrock-agent-runtime' client 执行rag操作：
import boto3


kb_id='OYWXI5HX47'

patient_ids = []

def create_user(user_data, user_type):
    user_ids = []
    pass
    return user_ids

doctor_ids = create_user('doctor')
patient_ids = create_user('patient')

'''
In this example we are going to use the retrieve and generate API. 
This API queries a knowledge base and generates responses based on the retrieved results, using an LLM.

'''
bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')
# retrieve and generate API
response = bedrock_agent_runtime_client.retrieve_and_generate(
    input={
        "text": "Who is Kelly?"
    },
    retrieveAndGenerateConfiguration={
        "type": "KNOWLEDGE_BASE",
        "knowledgeBaseConfiguration": {
            'knowledgeBaseId': kb_id,
            "modelArn": "arn:aws:bedrock:{}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0".format(region),
            "retrievalConfiguration": {
                "vectorSearchConfiguration": {
                    "numberOfResults":5,
                    "filter": {
                        "equals": {
                            "key": "patient_id",
                            "value": patient_ids[0]
                        }
                    }
                } 
            }
        }
    }
)

print(response['output']['text'],end='\n'*2)


'''
In this second example we are going to use the retrieve API. 
This API queries the knowledge base and retrieves relavant information from it, it does not generate the response.

'''

response_ret = bedrock_agent_runtime_client.retrieve(
    knowledgeBaseId=kb_id, 
    nextToken='string',
    retrievalConfiguration={
        "vectorSearchConfiguration": {
            "numberOfResults":3,
            "filter": {
                 "equals": {
                    "key": "patient_id",
                    "value": patient_ids[0]
                        }
                    }
                } 
            },
    retrievalQuery={
        'text': 'Who is Kelly?'
            
        }
)


def response_print(retrieve_resp):
#structure 'retrievalResults': list of contents
# each list has content,location,score,metadata
    for num,chunk in enumerate(response_ret['retrievalResults'],1):
        print(f'Chunk {num}: ',chunk['content']['text'],end='\n'*2)
        print(f'Chunk {num} Location: ',chunk['location'],end='\n'*2)
        print(f'Chunk {num} Score: ',chunk['score'],end='\n'*2)
        print(f'Chunk {num} Metadata: ',chunk['metadata'],end='\n'*2)

response_print(response_ret)