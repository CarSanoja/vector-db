#!/usr/bin/env python3
"""
Persistence example: Demonstrating crash recovery and persistence.
"""

import asyncio
import os
import shutil
from pathlib import Path
from uuid import uuid4

os.environ['VECTOR_DB_DATA_DIR'] = str(Path.cwd() / 'examples' / 'data')

from datetime import UTC, datetime

from src.domain.entities.library import IndexType, Library
from src.infrastructure.persistence.recovery import get_recovery_service
from src.services.persistence_aware_service import PersistentServiceFactory


async def cleanup_persistence_data():
    """Clean up all persistence data before running example."""
    data_root = Path.cwd() / 'examples' / 'data'

    dirs_to_clean = [
        data_root / 'wal',
        data_root / 'snapshots',
        Path('data') / 'wal',
        Path('data') / 'snapshots',
    ]
    for dir_path in dirs_to_clean:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"Cleaned up: {dir_path}")

    data_root.mkdir(parents=True, exist_ok=True)


async def main():
    """Demonstrate persistence and recovery."""
    print("=== Persistence and Recovery Example ===\n")

    await cleanup_persistence_data()

    PersistentServiceFactory._initialized = False
    PersistentServiceFactory._persistence_manager = None
    PersistentServiceFactory._library_repository = None
    PersistentServiceFactory._chunk_repository = None
    PersistentServiceFactory._library_service = None
    PersistentServiceFactory._chunk_service = None
    PersistentServiceFactory._search_service = None

    print("\nPhase 1: Creating data with persistence\n")

    await PersistentServiceFactory.initialize()
    library_repo = PersistentServiceFactory.get_library_repository()

    libraries_created = []
    for i in range(3):
        library = Library(
            id=uuid4(),
            name=f"Persistent Library {i}",
            dimension=128,
            index_type=IndexType.HNSW,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata={"persistent": True, "index": i}
        )
        lib, created = await library_repo.get_or_create(library)
        if created:
            print("Created", lib.id)
        else:
            print("Already exist:", lib.id)
        libraries_created.append(library)
        print(f"Created: {library.name}")

    print(f"\nTotal libraries before shutdown: {await library_repo.count()}")

    recovery = get_recovery_service()
    backup_id = await recovery.create_backup("Manual backup before shutdown")
    print(f"Created backup: {backup_id}")

    print("\nShutting down services...")
    await PersistentServiceFactory.shutdown()

    print("\n\nPhase 2: Simulating crash and recovery\n")

    PersistentServiceFactory._initialized = False
    PersistentServiceFactory._persistence_manager = None
    PersistentServiceFactory._library_repository = None

    await PersistentServiceFactory.initialize()
    library_repo2 = PersistentServiceFactory.get_library_repository()

    recovered_count = await library_repo2.count()
    print(f"Libraries recovered: {recovered_count}")

    print("\nVerifying recovered libraries:")
    for original in libraries_created:
        recovered = await library_repo2.get(original.id)
        if recovered:
            print(f"✓ {recovered.name} - Successfully recovered")
            print(f"  Metadata: {recovered.metadata}")
        else:
            print(f"✗ {original.name} - NOT FOUND!")

    print("\n\nPhase 3: Adding data after recovery")

    new_library = Library(
        id=uuid4(),
        name="Post-Recovery Library",
        dimension=256,
        index_type=IndexType.LSH,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        metadata={"created_after_recovery": True}
    )
    await library_repo2.get_or_create(new_library)
    print(f"Created: {new_library.name}")

    final_count = await library_repo2.count()
    print(f"\nFinal library count: {final_count}")

    recovery2 = get_recovery_service()
    consistency = await recovery2.verify_consistency()
    print(f"\nSystem consistency: {'✓ Consistent' if consistency['consistent'] else '✗ Inconsistent'}")
    print(f"Stats: {consistency['stats']}")

    await PersistentServiceFactory.shutdown()

    print("\n✓ Persistence example complete!")


if __name__ == "__main__":
    asyncio.run(main())
