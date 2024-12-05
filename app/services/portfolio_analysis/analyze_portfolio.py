import asyncio
import io
import logging
from enum import Enum
from typing import Dict

from openai import AsyncAzureOpenAI

from app.config import settings
from app.schemas.portfolio_analysis_request import PortfolioAnalysisRequest,PortfolioInputs
from app.services.portfolio_analysis.portfolio_analyzer import PortfolioAnalyzer
from app.services.portfolio_analysis.portfolio_single_analysis import PortfolioAnalysis
from app.services.portfolio_analysis.prompt import (
    general_system_message,
    market_outlook,
    prompt_template_full_report,
    prompt_templates_arbitrage_scenario,
    prompt_templates,
    prompt_templates_executive_summary,
    market_future_performance,
    market_past_performance,
    summary_system_message,
)

class PortfolioTopic(Enum):
    EXECUTIVE_SUMMARY = "executive_summary"
    RISK_PROFILE = "risk_profile_alignment"
    ASSET_ALLOCATION = "asset_allocation"
    GEOGRAPHICAL_ALLOCATION = "geographical_allocation"
    SECTOR_ALLOCATION = "sector_allocation"
    SDG_SUMMARY = "sdg_summary"
    SDFDR_SUMMARY = "sfdr_summary"
    PAI_SUMMARY = "pai_summary"

async def analyze_portfolio_for_simulated_arbitrage(
        file_stream: io.BytesIO,
        portfolio_analysis_request:PortfolioAnalysisRequest,
        oai_client: AsyncAzureOpenAI
) -> str:
    portfolio = PortfolioAnalyzer(
        file_stream, portfolio_weights=dict(portfolio_analysis_request.weights)
    )
    full_data_string = portfolio.generate_data_string()
    client_risk_profile = portfolio.get_risk_profile()
    client_name = portfolio.get_client_name()
    portfolio_code_string = portfolio_analysis_request.format_weights()
    
    prompt = prompt_templates_arbitrage_scenario.format(
        portfolio_code = portfolio_code_string,
        client_risk_profile= client_risk_profile,
        client_name=client_name,
        market_outlook=market_outlook,
        full_data_string=full_data_string, 
        language=portfolio_analysis_request.language
    )
    system_prompt  = general_system_message.format(language = portfolio_analysis_request.full_language_name)
    async with oai_client:
        response = await generate_openai_response(oai_client, system_message=system_prompt, llm_prompt=prompt)
    return response

async def prepare_prompt_es_v1(file_stream: io.BytesIO, portfolio_analysis_request:PortfolioInputs):
    portfolio = PortfolioAnalysis(
        file_stream, portfolio_weights=dict(portfolio_analysis_request.weights))
    full_data_string = portfolio.generate_data_port()
    client_risk_profile = portfolio.get_risk_profile()
    client_name = portfolio.get_client_name()
    profile = portfolio.profils.iloc[0]
    profile_doc, all_pais, all_sdgs = portfolio._build_profile_documentation_part(profile, portfolio.product_ESG_data)
    client_portfolio=portfolio._generate_portfolio(profile)
    sector_info=portfolio._generate_sector_allocations(portfolio.product_allocation)
    geograph_info=portfolio._generate_geographical_allocations(portfolio.product_allocation)
    asset_info=portfolio._generate_asset_allocations(portfolio.product_allocation)
    safir_info=portfolio._generate_safir(portfolio.product_ESG_data)
    sdg_info=portfolio._generate_SDG(all_sdgs, portfolio.product_ESG_data)
    pais_info=portfolio._generate_PAI(all_pais, portfolio.product_ESG_data)
    taxonomy_info=portfolio._generate_taxonomy(portfolio.product_ESG_data, profile)
    sfdr_info=portfolio._generate_sfdr(portfolio.product_ESG_data, profile)
    performance_info=portfolio._generate_yearly_performance_string(portfolio.portfolios, portfolio.financial_data)
    portfolio_code_string = str(portfolio_analysis_request.weights)
    prompt = prompt_templates_executive_summary.format(
        client_info=profile_doc,
        client_portfolio=client_portfolio,
        portfolio_code = portfolio_code_string,
        sector_info=sector_info,
        geograph_info=geograph_info,
        asset_info=asset_info,
        safir_info=safir_info,
        sdg_info=sdg_info,
        pais_info=pais_info,
        taxonomy_info=taxonomy_info,
        sfdr_info=sfdr_info,
        performance_info=performance_info,
        client_risk_profile= client_risk_profile,
        client_name=client_name,
        market_past_performance=market_past_performance,
        market_future_performance=market_future_performance,
        full_data_string=full_data_string,
        language = portfolio_analysis_request.language
    )
    system_prompt  = general_system_message.format(language = portfolio_analysis_request.full_language_name)
    return(prompt, system_prompt)

async def prepare_prompt_sa_v1(file_stream: io.BytesIO, portfolio_analysis_request:PortfolioAnalysisRequest):
    portfolio = PortfolioAnalyzer(
        file_stream, portfolio_weights=dict(portfolio_analysis_request.weights))
    full_data_string = portfolio.generate_data_string()
    client_risk_profile = portfolio.get_risk_profile()
    client_name = portfolio.get_client_name()
    portfolio_code_string = portfolio_analysis_request.format_weights()
    
    prompt = prompt_templates_arbitrage_scenario.format(
        portfolio_code = portfolio_code_string,
        client_risk_profile= client_risk_profile,
        client_name=client_name,
        market_outlook=market_outlook,
        full_data_string=full_data_string, 
        language=portfolio_analysis_request.language
    )
    system_prompt  = general_system_message.format(language = portfolio_analysis_request.full_language_name)
    return (prompt, system_prompt)

# async def make_portfolio_v1(prompt, system_prompt,
#         oai_client: AsyncAzureOpenAI
# ) -> str:
#     async with oai_client:
#         response = await generate_openai_response(oai_client, system_message=system_prompt, llm_prompt=prompt)
#     return response

async def analyze_portfolio(
    file_stream: io.BytesIO,
    portfolio_analysis_request: PortfolioAnalysisRequest,
    oai_client: AsyncAzureOpenAI,
) -> str:
    portfolio = PortfolioAnalyzer(
        file_stream, portfolio_weights=dict(portfolio_analysis_request.weights)
    )
    
    full_data_string = portfolio.generate_data_string()
    logging.info("Extracted and parsed data")

    async with oai_client:
        summaries = await generate_summaries(
            oai_client, full_data_string, market_outlook
        )
        return await generate_full_report(
            oai_client, summaries, portfolio_analysis_request.language
        )
    
async def analyze_portfolio_topic(
    topic: PortfolioTopic,
    file_stream: io.BytesIO,
    porfolio_analysis_request: PortfolioAnalysisRequest,
    oai_client: AsyncAzureOpenAI,
) -> str:
    portfolio = PortfolioAnalyzer(
        file_stream, portfolio_weights=dict(porfolio_analysis_request.weights)
    )
    full_data_string = portfolio.generate_data_string()
    logging.info("Extracted and parsed data")

    async with oai_client:
        return await generate_summary(
            topic, oai_client, full_data_string, market_outlook
        )

async def generate_openai_response(
    oai_client: AsyncAzureOpenAI, system_message: str, llm_prompt: str
) -> str:
    logging.info("Calling Azure OpenAI Endpoint..")
    response = await oai_client.chat.completions.create(
        model=settings.AZURE_OPENAI_MODEL_NAME,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": llm_prompt},
        ],
    )
    return response.choices[0].message.content  # type: ignore

async def generate_summaries(
    oai_client: AsyncAzureOpenAI, full_data_string: str, market_outlook: str
) -> Dict[PortfolioTopic, str]:
    prompt_tasks = {
        topic: prompt_templates[topic.value].format(
            market_outlook=market_outlook, full_data_string=full_data_string
        )
        for topic in PortfolioTopic
    }

    tasks = [
        generate_openai_response(oai_client, general_system_message, prompt)
        for prompt in prompt_tasks.values()
    ]
    results = await asyncio.gather(*tasks)
    return dict(zip(prompt_tasks.keys(), results))

async def generate_summary(
    topic: PortfolioTopic,
    oai_client: AsyncAzureOpenAI,
    full_data_string: str,
    market_outlook: str,
) -> str:
    prompt = prompt_templates[topic.value].format(
        market_outlook=market_outlook, full_data_string=full_data_string,
    )
    response = await generate_openai_response(
        oai_client, general_system_message, prompt
    )

    return response

async def generate_full_report(
    oai_client: AsyncAzureOpenAI, summaries: Dict[PortfolioTopic, str], language: str
) -> str:
    logging.info(f"Generating full report in {language} language")

    full_report_prompt = prompt_template_full_report.format(
        executive_summary=summaries[PortfolioTopic.EXECUTIVE_SUMMARY],
        risk_profile=summaries[PortfolioTopic.RISK_PROFILE],
        asset_allocation=summaries[PortfolioTopic.ASSET_ALLOCATION],
        geographical_allocation=summaries[PortfolioTopic.GEOGRAPHICAL_ALLOCATION],
        sector_allocation=summaries[PortfolioTopic.SECTOR_ALLOCATION],
        sdg_summary=summaries[PortfolioTopic.SDG_SUMMARY],
        sdfdr_summary=summaries[PortfolioTopic.SDFDR_SUMMARY],
        pai_summary=summaries[PortfolioTopic.PAI_SUMMARY],
        language=language,
    )

    return await generate_openai_response(
        oai_client, summary_system_message, full_report_prompt
    )