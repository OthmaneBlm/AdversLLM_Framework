import io
import json, sys
from enum import Enum
import markdown_to_json
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, FastAPI
from fastapi.responses import Response
from openai import AsyncAzureOpenAI
from pydantic import ValidationError, BaseModel
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.dependencies import initialize_openai_client, init_openai_client
from app.schemas.portfolio_analysis_request import PortfolioAnalysisRequest, PortfolioInputs
from app.services.portfolio_analysis.AWS_models import initiate_AWS, mistral_response, Amazon_Titan_response, Anthropic_response
from app.services.portfolio_analysis.analyze_portfolio import (
    PortfolioTopic,
    analyze_portfolio,
    analyze_portfolio_topic,
    prepare_prompt_es_v1,
    generate_openai_response,
    prepare_prompt_sa_v1
)

class Language(str, Enum):
    en="en"
    fr="fr"
    nl="nl"

router = APIRouter()

class ModelName(str, Enum):
    Azure = "Azure"
    Amazon = "Amazon"
    Anthropic = "Anthropic"
    Mistral = "Mistral"

# @router.get("/")
# async def select_model(model_name: ModelName):
#     return {"model_name": model_name.value}

# @router.post("/analyze")
# async def analyze(
#     file: UploadFile = File(...),
#     portfolio_metadata: str = Form(...),
#     oai_client: AsyncAzureOpenAI = Depends(initialize_openai_client),
# ):
#     if not file or not file.filename or not file.filename.endswith(".xlsx"):
#         raise HTTPException(
#             status_code=400, detail="Invalid file format. Please upload an Excel file."
#         )

#     try:
#         portfolio_metadata_request = json.loads(portfolio_metadata)
#         porfolio_analysis_request = PortfolioAnalysisRequest(
#             **portfolio_metadata_request
#         )
#     except json.JSONDecodeError:
#         raise HTTPException(
#             status_code=400, detail="Malformed JSON in portfolio_request"
#         )

#     except ValidationError as e:
#         raise HTTPException(
#             status_code=422,
#             detail=f"Validation error in portfolio_request: {e.errors()}",
#         )

#     file_contents = await file.read()
#     file_stream = io.BytesIO(file_contents)

#     response = await analyze_portfolio(
#         file_stream, porfolio_analysis_request, oai_client
#     )
#     return Response(content=response, media_type="text/markdown")


# @router.post("/analyze_topic/{topic}")
# async def analyze_topic(
#     topic: PortfolioTopic,
#     file: UploadFile = File(...),
#     portfolio_metadata: str = Form(...),
#     oai_client: AsyncAzureOpenAI = Depends(initialize_openai_client),
# ):
#     if not file or not file.filename or not file.filename.endswith(".xlsx"):
#         raise HTTPException(
#             status_code=400, detail="Invalid file format. Please upload an Excel file."
#         )

#     try:
#         portfolio_metadata_request = json.loads(portfolio_metadata)
#         porfolio_analysis_request = PortfolioAnalysisRequest(
#             **portfolio_metadata_request
#         )
#     except json.JSONDecodeError:
#         raise HTTPException(
#             status_code=400, detail="Malformed JSON in portfolio_request"
#         )

#     except ValidationError as e:
#         raise HTTPException(
#             status_code=422,
#             detail=f"Validation error in portfolio_request: {e.errors()}",
#         )

#     file_contents = await file.read()
#     file_stream = io.BytesIO(file_contents)

#     response = await analyze_portfolio_topic(
#         topic, file_stream, porfolio_analysis_request, oai_client
#     )
#     return Response(content=response, media_type="text/markdown")

@router.post("/summary")
async def executive_summary(
    File: UploadFile = File(...),
    Portfolio: str = Form(...),
    Language: Language = Form(...),
    LLM_type: ModelName = Form(...),
):
    if not file or not File.filename or not File.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload an Excel file.")
    try:
        portfolio_metadata='{"weights": {"Current": {' + Portfolio + '}}, "language": "' + Language.value + '"}'
        #print('*** metadata here', portfolio_metadata)
        portfolio_metadata_request = json.loads(portfolio_metadata)
        porfolio_analysis_request = PortfolioInputs(**portfolio_metadata_request)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400, detail="Malformed JSON in portfolio_request")
    except ValidationError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Validation error in portfolio_request: {e.errors()}")
    file_contents = await File.read()
    file_stream = io.BytesIO(file_contents)
    prompt, system_prompt = await prepare_prompt_es_v1(file_stream, porfolio_analysis_request)

    if LLM_type.value == 'Azure':
        oai_client = await init_openai_client()
        response = await generate_openai_response(oai_client, system_prompt, prompt)
    else:
        client = await initiate_AWS()
        if LLM_type.value == 'Amazon':
            response = await Amazon_Titan_response(system_prompt, prompt, client)
        elif LLM_type.value == 'Anthropic':
            response = await Anthropic_response(system_prompt, prompt, client)
        elif LLM_type.value == 'Mistral':
            print("Using model:", LLM_type.value)
            response = await mistral_response(system_prompt, prompt, client)
    # print output to a json file as well
    json_response=markdown_to_json.dictify(response)
    #return Response(content=response, media_type="text/markdown")
    return JSONResponse(content=json_response)

@router.post("/simulate_arbitrage")
async def simulate_arbitrage(
    File: UploadFile = File(...),
    Portfolio: str = Form(...),
    Simulated_Portfolio: str = Form(...),
    Language: Language = Form(...),
    LLM_type: ModelName = Form(...)
):
    if not File or not File.filename or not File.filename.endswith(".xlsx"):
        raise HTTPException(
            status_code=400, detail="Invalid file format. Please upload an Excel file.")
    try:
        portfolio_metadata='{"weights": {"Current": {' + Portfolio + '},"Simulated": {' + Simulated_Portfolio + '}}, "language": "' + Language.value + '"}'
        portfolio_metadata_request = json.loads(portfolio_metadata)
        porfolio_analysis_request = PortfolioAnalysisRequest(**portfolio_metadata_request)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400, detail="Malformed JSON in portfolio_request")

    except ValidationError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Validation error in portfolio_request: {e.errors()}")

    file_contents = await File.read()
    file_stream = io.BytesIO(file_contents)

    prompt, system_prompt = await prepare_prompt_sa_v1(file_stream, porfolio_analysis_request)

    if LLM_type.value == 'Azure':
        oai_client = await init_openai_client()
        response = await generate_openai_response(oai_client, system_prompt, prompt)
    else:
        client = await initiate_AWS()
        if LLM_type.value == 'Amazon':
            response = await Amazon_Titan_response(system_prompt, prompt, client)
        elif LLM_type.value == 'Anthropic':
            response = await Anthropic_response(system_prompt, prompt, client)
        elif LLM_type.value == 'Mistral':
            print("Using model:", LLM_type.value)
            response = await mistral_response(system_prompt, prompt, client)

    json_response=markdown_to_json.dictify(response)
    #return Response(content=response, media_type="text/markdown")
    return JSONResponse(content=json_response)