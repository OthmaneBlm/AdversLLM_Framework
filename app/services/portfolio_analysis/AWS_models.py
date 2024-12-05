import boto3, json
from botocore.exceptions import ClientError

async def initiate_AWS():
    boto3.Session(profile_name="evd")
    client = boto3.client("bedrock-runtime", region_name="eu-west-3")
    return(client)

async def mistral_response(general_system_message, prompt, client):
    model_id = "mistral.mistral-7b-instruct-v0:2"
    formatted_prompt = f"<s>[INST] {general_system_message + prompt} [/INST]"
    native_request = {"prompt": formatted_prompt, "temperature": 0.5,}
    request = json.dumps(native_request)
    try:
        response = client.invoke_model(modelId=model_id, body=request)
    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        exit(1)
    model_response = json.loads(response["body"].read())
    response = model_response["outputs"][0]["text"]
    return(response)

async def AI21_response(general_system_message, prompt, client):
    # Only in US east
    model_id = "ai21.jamba-1-5-large-v1:0"
    native_request = {
  "messages": [{
      "role":"system",
      "content":general_system_message},
    {"role":"user",
      "content":prompt}],
  "temperature": 0.5,
  "n":1}
    request = json.dumps(native_request)
    try:
        response = client.invoke_model(modelId=model_id, body=request)
    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        exit(1)
    model_response = json.loads(response["body"].read())
    response = model_response["choices"][0]["message"]["content"]
    return(response)

async def Amazon_Titan_response(general_system_message, prompt, client):
    model_id = "amazon.titan-text-express-v1"
    native_request = {
        "inputText": general_system_message+prompt,
        "textGenerationConfig": {
            "temperature": 0.5,
        },}
    request = json.dumps(native_request)
    try:
        response = client.invoke_model(modelId=model_id, body=request)
    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        exit(1)
    model_response = json.loads(response["body"].read())
    response = model_response["results"][0]["outputText"]
    return(response)

async def Anthropic_response(general_system_message, prompt, client):
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"
    native_request = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 15000,
        "temperature": 0.5,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": general_system_message+prompt}],
            }],}
    request = json.dumps(native_request)
    try:
        response = client.invoke_model(modelId=model_id, body=request)
    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        exit(1)
    model_response = json.loads(response["body"].read())
    response = model_response["content"][0]["text"]
    return(response)

async def Cohere_response(general_system_message, prompt, client):
    # Only in US
    model_id = "cohere.command-r-v1:0"
    native_request = {
        "message": general_system_message+prompt,
        "temperature": 0.5}
    request = json.dumps(native_request)
    try:
        response = client.invoke_model(modelId=model_id, body=request)
    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        exit(1)
    model_response = json.loads(response["body"].read())
    response = model_response["text"]
    return(response)

async def Llama_response(general_system_message, prompt, client):
    model_id = "meta.llama3-8b-instruct-v1:0"
    formatted_prompt = f"""
    <|begin_of_text|><|start_header_id|>user<|end_header_id|>
    {general_system_message+prompt}
    <|eot_id|>
    <|start_header_id|>assistant<|end_header_id|>
    """
    native_request = {
        "prompt": formatted_prompt,
        "temperature": 0.5}
    request = json.dumps(native_request)
    try:
        response = client.invoke_model(modelId=model_id, body=request)
    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        exit(1)
    model_response = json.loads(response["body"].read())
    response = model_response["generation"]
    return(response)