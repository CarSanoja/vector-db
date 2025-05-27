#!/usr/bin/env python3
import asyncio
import json
import os
import uuid
from typing import Any, dict, list

import cohere
import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_API_URL: str = os.getenv("VECTOR_DB_API_URL", "http://localhost:8000")
API_V1_PREFIX: str = "/api/v1"

COHERE_API_KEY: str | None = os.getenv("COHERE_API_KEY")
COHERE_MODEL: str = "embed-english-light-v3.0"
EMBEDDING_DIMENSION: int = 384  # For 'embed-english-light-v3.0'
# For 'embed-english-v3.0' or 'embed-multilingual-v3.0',  1024

# --- Console Colors ---
GREEN: str = "\033[0;32m"
BLUE: str = "\033[0;34m"
YELLOW: str = "\033[1;33m"
RED: str = "\033[0;31m"
NC: str = "\033[0m"


# --- Helper Functions ---
def print_section(title: str) -> None:
    """Prints a formatted section title to the console."""
    print(f"\n{BLUE}{'=' * 10} {title.upper()} {'=' * 10}{NC}")


def print_response_data(
    response: httpx.Response, data: Any = None, success_status: int | None = None
) -> None:
    """Prints formatted HTTP response status and JSON data."""
    color = NC
    if success_status and response.status_code == success_status:
        color = GREEN
    elif 200 <= response.status_code < 300:
        color = YELLOW
    else:
        color = RED

    print(f"{color}Status Code: {response.status_code}{NC}")
    try:
        response_json = data if data is not None else response.json()
        print(json.dumps(response_json, indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print(f"Response Body: {response.text}")


async def get_cohere_embeddings(
    cohere_client: cohere.AsyncClient,
    texts: list[str],
    input_type: str = "search_document",
) -> list[list[float]]:
    """Generates embeddings for a list of texts using Cohere."""
    print(
        f"{YELLOW}Generating embeddings with Cohere for {len(texts)} text(s) (model: {COHERE_MODEL}, type: {input_type})...{NC}"
    )
    try:
        response = await cohere_client.embed(
            texts=texts, model=COHERE_MODEL, input_type=input_type
        )
        print(f"{GREEN}Embeddings generated successfully.{NC}")
        return response.embeddings
    except cohere.CohereError as e:
        print(f"{RED}Cohere API Error during embedding generation: {e}{NC}")
        raise


async def create_library(
    api_client: httpx.AsyncClient, name: str, dimension: int
) -> str:
    """Creates a new library via the API."""
    print_section(f"Creating Library: {name} (Dimension: {dimension})")
    library_payload = {"name": name, "dimension": dimension, "index_type": "HNSW"}
    response = await api_client.post(
        f"{API_V1_PREFIX}/libraries/", json=library_payload
    )
    created_library_data = response.json()
    print_response_data(response, created_library_data, success_status=201)
    response.raise_for_status()
    return created_library_data["id"]


async def add_chunks_in_bulk(
    api_client: httpx.AsyncClient,
    library_id: str,
    document_texts: list[str],
    embeddings: list[list[float]],
) -> list[str]:
    """Adds documents as chunks in bulk to a library via the API."""
    print_section(
        f"Adding {len(document_texts)} Chunks in Bulk to Library: {library_id}"
    )
    chunks_to_create = []
    for i, text in enumerate(document_texts):
        chunks_to_create.append(
            {
                "content": text,
                "embedding": embeddings[i],
                "metadata": {"source": "cohere_example", "doc_index": i},
            }
        )

    bulk_payload = {"chunks": chunks_to_create}
    response = await api_client.post(
        f"{API_V1_PREFIX}/libraries/{library_id}/chunks/bulk", json=bulk_payload
    )
    created_chunks_data = response.json()
    print_response_data(response, created_chunks_data, success_status=201)
    response.raise_for_status()
    return [chunk["id"] for chunk in created_chunks_data]


async def trigger_library_index_build(
    api_client: httpx.AsyncClient, library_id: str
) -> None:
    """Triggers the index build process for a library via the API."""
    print_section(f"Triggering Index Build for Library: {library_id}")
    response = await api_client.post(f"{API_V1_PREFIX}/libraries/{library_id}/index")
    print_response_data(response, success_status=202)
    response.raise_for_status()


async def search_library(
    api_client: httpx.AsyncClient,
    library_id: str,
    query_embedding: list[float],
    k_results: int,
) -> list[dict[str, Any]]:
    """Performs a vector search in a library via the API."""
    print_section(f"Searching in Library: {library_id} (Top {k_results} results)")
    search_payload = {"embedding": query_embedding, "k": k_results}
    response = await api_client.post(
        f"{API_V1_PREFIX}/libraries/{library_id}/search", json=search_payload
    )
    search_results_data = response.json()
    print_response_data(response, search_results_data, success_status=200)
    response.raise_for_status()
    return search_results_data.get("results", [])


async def delete_library(api_client: httpx.AsyncClient, library_id: str) -> None:
    """Deletes a library via the API."""
    print_section(f"Deleting Library (Cleanup): {library_id}")
    response = await api_client.delete(f"{API_V1_PREFIX}/libraries/{library_id}")
    print_response_data(response, success_status=204)
    if response.status_code != 204:
        print(f"{RED}Failed to delete library {library_id} properly.{NC}")


async def run_cohere_example_flow():
    """Main flow for the Cohere embedding example."""
    if not COHERE_API_KEY:
        print(
            f"{RED}CRITICAL ERROR: COHERE_API_KEY environment variable not set. This example cannot run.{NC}"
        )
        return

    library_id: str | None = None
    temp_library_name = f"Cohere-Real-Embed-Lib-{uuid.uuid4().hex[:6]}"

    texts_to_index: list[str] = [
        "The vibrant city of Barcelona is known for its unique architecture and lively atmosphere.",
        "Paella, a traditional Spanish rice dish, is a culinary delight often enjoyed with seafood.",
        "Exploring ancient Roman ruins can be a fascinating journey into history.",
        "Modern artificial intelligence models are capable of generating human-quality text and images.",
        "Playing football on the sunny beaches of Spain is a popular recreational activity.",
    ]
    search_query_text: str = "What are some famous Spanish foods and landmarks?"

    async with (
        cohere.AsyncClient(COHERE_API_KEY) as cohere_client,
        httpx.AsyncClient(base_url=BASE_API_URL, timeout=60.0) as api_client,
    ):
        try:
            print_section("Starting Cohere Real Embeddings API Example")

            library_id = await create_library(
                api_client, temp_library_name, EMBEDDING_DIMENSION
            )

            document_embeddings = await get_cohere_embeddings(
                cohere_client, texts_to_index, input_type="search_document"
            )

            await add_chunks_in_bulk(
                api_client, library_id, texts_to_index, document_embeddings
            )

            await trigger_library_index_build(api_client, library_id)

            print(
                f"{YELLOW}Waiting briefly to allow potential indexing or propagation...{NC}"
            )
            await asyncio.sleep(2)

            query_embedding_list = await get_cohere_embeddings(
                cohere_client, [search_query_text], input_type="search_query"
            )
            query_embedding = query_embedding_list[0]

            search_results = await search_library(
                api_client, library_id, query_embedding, k_results=3
            )

            print_section(f'Search Results for Query: "{search_query_text}"')
            if search_results:
                for i, result in enumerate(search_results):
                    print(
                        f"  {i + 1}. Score: {result.get('score', 'N/A'):.4f}, "
                        f"Distance: {result.get('distance', 'N/A'):.4f}"
                    )
                    print(f'     Content: "{result.get("content", "")}"')
                    print(f"     Metadata: {result.get('metadata', {})}")
            else:
                print(f"{YELLOW}No search results found.{NC}")

            print(
                f"\n{GREEN}✓ Cohere Real Embeddings API Example completed successfully!{NC}"
            )

        except ValueError as ve:
            print(f"\n{RED}CONFIGURATION ERROR: {ve}{NC}")
        except httpx.HTTPStatusError as http_err:
            print(
                f"\n{RED}API HTTP Error: Status {http_err.response.status_code} on {http_err.request.url}{NC}"
            )
            print_response_data(http_err.response)
        except httpx.RequestError as req_err:
            print(
                f"\n{RED}API Request Error: Could not connect to {req_err.request.url}. Is the server running?{NC}"
            )
        except cohere.CohereError as co_err:
            err_body_msg = (
                co_err.body.get("message")
                if hasattr(co_err, "body") and isinstance(co_err.body, dict)
                else "N/A"
            )
            print(
                f"\n{RED}Cohere API Error: {co_err} (Status: {co_err.http_status}, Message: {err_body_msg}){NC}"
            )
        except Exception as e:
            print(f"\n{RED}An unexpected error occurred: {type(e).__name__} - {e}{NC}")
        finally:
            if library_id:
                await delete_library(api_client, library_id)
            print_section("Example Flow Finished")


if __name__ == "__main__":
    asyncio.run(run_cohere_example_flow())
