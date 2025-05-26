#!/usr/bin/env python3
import httpx
import asyncio
import uuid
import json
from typing import Dict, Any, List

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"


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

async def create_temp_library(client: httpx.AsyncClient) -> str:
    lib_name = f"Chunk-Test-Lib-{uuid.uuid4().hex[:8]}"
    lib_data = {"name": lib_name, "dimension": 4, "index_type": "HNSW"}
    response = await client.post(f"{API_PREFIX}/libraries/", json=lib_data)
    response.raise_for_status() 
    return response.json()["id"]

async def delete_temp_library(client: httpx.AsyncClient, library_id: str):
    await client.delete(f"{API_PREFIX}/libraries/{library_id}")
    print(f"Temporary library {library_id} deleted.")

async def main():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        library_id = None
        chunk_id = None
        bulk_chunk_ids: List[str] = []

        try:
            print_section("0. Create Temporary Library for Chunks")
            library_id = await create_temp_library(client)
            print(f"Temporary library created with ID: {library_id}")

            print_section("1. Create Chunk")
            chunk_data = {
                "content": "This is the first test chunk.",
                "embedding": [0.1, 0.2, 0.3, 0.4],
                "metadata": {"source": "test_script_02"}
            }
            response = await client.post(f"{API_PREFIX}/libraries/{library_id}/chunks", json=chunk_data)
            created_chunk = response.json()
            print_response(response, created_chunk)
            assert response.status_code == 201
            chunk_id = created_chunk.get("id")
            assert chunk_id is not None

            print_section(f"2. Get Chunk by ID: {chunk_id}")
            response = await client.get(f"{API_PREFIX}/chunks/{chunk_id}")
            print_response(response)
            assert response.status_code == 200
            assert response.json().get("content") == chunk_data["content"]

            print_section(f"3. List Chunks in Library: {library_id}")
            response = await client.get(f"{API_PREFIX}/libraries/{library_id}/chunks?limit=5")
            print_response(response)
            assert response.status_code == 200
            listed_chunks = response.json().get("chunks", [])
            assert len(listed_chunks) >= 1
            assert any(c["id"] == chunk_id for c in listed_chunks)

            print_section(f"4. Update Chunk: {chunk_id}")
            update_data = {
                "content": "Updated chunk content.",
                "metadata": {"source": "test_script_02", "status": "updated"}
            }
            response = await client.put(f"{API_PREFIX}/chunks/{chunk_id}", json=update_data) 
            print_response(response)
            assert response.status_code == 200
            updated_chunk_data = response.json()
            assert updated_chunk_data.get("content") == update_data["content"]
            assert updated_chunk_data.get("metadata", {}).get("status") == "updated"

            print_section(f"5. Bulk Create Chunks in Library: {library_id}")
            bulk_create_data = {
                "chunks": [
                    {"content": "Bulk chunk A", "embedding": [0.5, 0.6, 0.7, 0.8], "metadata": {"bulk": "A"}},
                    {"content": "Bulk chunk B", "embedding": [0.9, 1.0, 1.1, 1.2], "metadata": {"bulk": "B"}},
                ]
            }
            response = await client.post(f"{API_PREFIX}/libraries/{library_id}/chunks/bulk", json=bulk_create_data)
            created_bulk_chunks = response.json()
            print_response(response, created_bulk_chunks)
            assert response.status_code == 201
            assert len(created_bulk_chunks) == 2
            bulk_chunk_ids = [c["id"] for c in created_bulk_chunks]

            print("\nSUCCESS: Chunk management tests passed!")

        except httpx.ConnectError:
            print("\nERROR: Could not connect to the API server. Is it running?")
        except AssertionError as e:
            print(f"\nASSERTION ERROR: {e}")
        except Exception as e:
            print(f"\nUNEXPECTED ERROR: {e}")
            if hasattr(e, 'response'):
                print_response(e.response) 
        finally:
            if chunk_id: 
                print_section(f"6. Delete Chunk (Cleanup): {chunk_id}")
                await client.delete(f"{API_PREFIX}/chunks/{chunk_id}")
                print(f"Chunk {chunk_id} deleted.")
            for bc_id in bulk_chunk_ids: 
                print_section(f"6. Delete Bulk Chunk (Cleanup): {bc_id}")
                await client.delete(f"{API_PREFIX}/chunks/{bc_id}")
                print(f"Chunk {bc_id} deleted.")
            if library_id:
                print_section(f"7. Delete Temporary Library (Cleanup): {library_id}")
                await delete_temp_library(client, library_id)


if __name__ == "__main__":
    asyncio.run(main())