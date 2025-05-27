#!/usr/bin/env python3
import asyncio
import json
import uuid
from typing import Any, dict

import httpx

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

def print_json(data: dict[str, Any]):
    print(json.dumps(data, indent=2, ensure_ascii=False))

async def main():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        library_id = None
        unique_name = f"Test-Library-{uuid.uuid4().hex[:8]}"
        updated_name = f"Updated-Test-Library-{uuid.uuid4().hex[:8]}"

        try:
            print_section("1. Create Library")
            library_data = {
                "name": unique_name,
                "dimension": 128,
                "index_type": "HNSW",
                "description": "A library for testing purposes.",
                "metadata": {"env": "test"}
            }
            response = await client.post(f"{API_PREFIX}/libraries/", json=library_data)
            created_library = response.json()
            print_response(response, created_library)
            assert response.status_code == 201
            library_id = created_library.get("id")
            assert library_id is not None

            print_section(f"2. Get Library by ID: {library_id}")
            response = await client.get(f"{API_PREFIX}/libraries/{library_id}")
            print_response(response)
            assert response.status_code == 200
            assert response.json().get("name") == unique_name

            print_section("3. list Libraries")
            response = await client.get(f"{API_PREFIX}/libraries/?limit=5")
            print_response(response)
            assert response.status_code == 200
            assert len(response.json().get("libraries", [])) > 0

            print_section(f"4. Update Library: {library_id}")
            update_data = {
                "name": updated_name,
                "description": "Updated description.",
                "metadata": {"status": "updated"}
            }
            response = await client.put(f"{API_PREFIX}/libraries/{library_id}", json=update_data)
            print_response(response)
            assert response.status_code == 200
            updated_library = response.json()
            assert updated_library.get("name") == updated_name
            assert updated_library.get("description") == "Updated description."
            assert updated_library.get("metadata", {}).get("status") == "updated"

            print_section(f"5. Rebuild Index for Library: {library_id}")
            response = await client.post(f"{API_PREFIX}/libraries/{library_id}/index")
            print_response(response)
            assert response.status_code == 202
            assert response.json().get("status") == "pending"

            print("\nSUCCESS: Library management tests passed!")

        except httpx.ConnectError:
            print("\nERROR: Could not connect to the API server. Is it running?")
        except AssertionError as e:
            print(f"\nASSERTION ERROR: {e}")
        except Exception as e:
            print(f"\nUNEXPECTED ERROR: {e}")
            if hasattr(e, 'response'):
                print_response(e.response) 
        finally:
            if library_id:
                print_section(f"6. Delete Library (Cleanup): {library_id}")
                response = await client.delete(f"{API_PREFIX}/libraries/{library_id}")

                print(f"Status Code: {response.status_code}")
                if response.status_code != 204:
                     print("Error during cleanup, library might not have been deleted.")
                     try:
                         print_json(response.json())
                     except Exception:
                         print(response.text)
                else:
                    print(f"Library {library_id} deleted successfully.")


if __name__ == "__main__":
    asyncio.run(main())
