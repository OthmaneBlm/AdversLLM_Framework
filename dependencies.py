from openai import AsyncAzureOpenAI

from app.config import settings

async def init_openai_client():
    return AsyncAzureOpenAI(api_key=settings.AZURE_OPENAI_API_KEY, api_version="2023-12-01-preview", azure_endpoint=settings.AZURE_OPENAI_ENDPOINT)


async def initialize_openai_client():
    client = AsyncAzureOpenAI(
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version="2023-12-01-preview",
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    )
    try:
        yield client
    finally:
        await client.close()