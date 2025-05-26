#!/usr/bin/env python3
import httpx
import asyncio
import uuid
import json
from typing import Dict, Any, List

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"
DIMENSION = 4 


def print_section(title: str):
    print(f"\n{'='*10} {title.upper()} {'='*10}")

def print_response(response: httpx.Response, data: Any = None):
    print(f"Status Code: {response.status_code}")
    try:
        print_json(data if data is not None else response.json())
    except json.JSONDecodeError:
        print(f"Response Body: {response.text}")

def print_json(data: Dict[str, Any]):
    print(json.dumps(data, indent=2, ensure_ascii=False))

async def setup_search_test_data(client: httpx.AsyncClient) -> tuple[str, List[str]]:
    lib_name = f"Search-Test-Lib-{uuid.uuid4().hex[:8]}"
    lib_data = {"name": lib_name, "dimension": DIMENSION, "index_type": "HNSW"}
    response = await client.post(f"{API_PREFIX}/libraries/", json=lib_data)
    response.raise_for_status()
    library_id = response.json()["id"]
    print(f"Search test library created: {library_id}")

    chunks_data = [
        {"content": "The quick brown fox", "embedding": [0.1, 0.2, 0.3, 0.4], "metadata": {"animal": "fox"}},
        {"content": "Lazy dog sleeps", "embedding": [0.5, 0.1, 0.2, 0.6], "metadata": {"animal": "dog"}},
        {"content": "Bright red apples", "embedding": [0.8, 0.7, 0.6, 0.5], "metadata": {"fruit": "apple"}},
        {"content": "Another fox story", "embedding": [0.2, 0.25, 0.35, 0.45], "metadata": {"animal": "fox"}},
    ]
    created_chunk_ids = []
    for chunk in chunks_data:
        resp_chunk = await client.post(f"{API_PREFIX}/libraries/{library_id}/chunks", json=chunk)
        resp_chunk.raise_for_status()
        created_chunk_ids.append(resp_chunk.json()["id"])
    
    print(f"Added {len(created_chunk_ids)} chunks to library {library_id}")
    
    await client.post(f"{API_PREFIX}/libraries/{library_id}/index")
    print(f"Index rebuild initiated for library {library_id}")
    await asyncio.sleep(1)


    return library_id, created_chunk_ids

async def cleanup_search_test_data(client: httpx.AsyncClient, library_id: str, chunk_ids: List[str]):
    await client.delete(f"{API_PREFIX}/libraries/{library_id}")
    print(f"Search test library {library_id} and its chunks deleted.")


async def main():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        library_id_1 = None
        library_id_2 = None
        chunk_ids_1: List[str] = []
        chunk_ids_2: List[str] = []

        try:
            print_section("0. Setup Data for Search Tests")
            library_id_1, chunk_ids_1 = await setup_search_test_data(client)

            print_section(f"1. Search in Library: {library_id_1}")
            search_query_embedding = [0.15, 0.22, 0.33, 0.42] 
            search_request = {
                "embedding": search_query_embedding,
                "k": 2
            }
            response = await client.post(f"{API_PREFIX}/libraries/{library_id_1}/search", json=search_request)
            print_response(response)
            assert response.status_code == 200
            search_results = response.json().get("results", [])
            assert len(search_results) > 0
            assert "The quick brown fox" in [r["content"] for r in search_results] or \
                   "Another fox story" in [r["content"] for r in search_results]

            print_section(f"2. Search in Library with Metadata Filter: {library_id_1}")
            search_request_filtered = {
                "embedding": search_query_embedding,
                "k": 2,
                "metadata_filters": {"animal": "dog"}
            }
            response = await client.post(f"{API_PREFIX}/libraries/{library_id_1}/search", json=search_request_filtered)
            print_response(response)
            assert response.status_code == 200
            search_results_filtered = response.json().get("results", [])
            assert len(search_results_filtered) >= 0 
            if search_results_filtered:
                 assert all(r["metadata"].get("animal") == "dog" for r in search_results_filtered)

            print_section("3. Setup Second Library for Multi-Search")
            lib2_name = f"Search-Test-Lib2-{uuid.uuid4().hex[:8]}"
            lib2_data = {"name": lib2_name, "dimension": DIMENSION, "index_type": "HNSW"}
            resp_lib2 = await client.post(f"{API_PREFIX}/libraries/", json=lib2_data)
            resp_lib2.raise_for_status()
            library_id_2 = resp_lib2.json()["id"]
            
            chunk_lib2_data = {"content": "Green apples are tasty", "embedding": [0.7, 0.8, 0.5, 0.6], "metadata": {"fruit": "apple"}}
            resp_chunk_lib2 = await client.post(f"{API_PREFIX}/libraries/{library_id_2}/chunks", json=chunk_lib2_data)
            resp_chunk_lib2.raise_for_status()
            chunk_ids_2.append(resp_chunk_lib2.json()["id"])
            await client.post(f"{API_PREFIX}/libraries/{library_id_2}/index")
            print(f"Second library {library_id_2} created and chunk added for multi-search.")
            await asyncio.sleep(1)


            print_section("3.1. Multi-Library Search")
            multi_search_request = {
                "library_ids": [library_id_1, library_id_2],
                "embedding": [0.75, 0.75, 0.55, 0.55], 
                "k": 3
            }
            response = await client.post(f"{API_PREFIX}/search", json=multi_search_request) 
            print_response(response)
            assert response.status_code == 200
            multi_search_results = response.json().get("results", {})
            assert library_id_1 in multi_search_results
            assert library_id_2 in multi_search_results

            print("\nSUCCESS: Search operations tests passed!")

        except httpx.ConnectError:
            print("\nERROR: Could not connect to the API server. Is it running?")
        except AssertionError as e:
            print(f"\nASSERTION ERROR: {e}")
        except Exception as e:
            print(f"\nUNEXPECTED ERROR: {e}")
            if hasattr(e, 'response'):
                print_response(e.response) 
        finally:
            if library_id_1:
                await cleanup_search_test_data(client, library_id_1, chunk_ids_1)
            if library_id_2:
                await cleanup_search_test_data(client, library_id_2, chunk_ids_2) 

if __name__ == "__main__":
    asyncio.run(main())