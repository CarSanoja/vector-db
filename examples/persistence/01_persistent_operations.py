#!/usr/bin/env python3
"""
Persistence example: Demonstrating crash recovery and persistence.
"""

import asyncio
import shutil
from pathlib import Path
from uuid import uuid4
import numpy as np

from src.services.persistence_aware_service import PersistentServiceFactory
from src.infrastructure.persistence.recovery import get_recovery_service
from src.domain.entities.library import Library, IndexType
from datetime import datetime, UTC


async def main():
    """Demonstrate persistence and recovery."""
    print("=== Persistence and Recovery Example ===\n")
    
    # Clean up any existing data
    data_dir = Path("examples/data")
    if data_dir.exists():
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Phase 1: Create data with persistence
    print("Phase 1: Creating data with persistence\n")
    
    # Initialize services with persistence
    await PersistentServiceFactory.initialize()
    library_repo = PersistentServiceFactory.get_library_repository()
    
    # Create libraries
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
        await library_repo.create(library)
        libraries_created.append(library)
        print(f"Created: {library.name}")
    
    print(f"\nTotal libraries before shutdown: {await library_repo.count()}")
    
    # Create a backup
    recovery = get_recovery_service()
    backup_id = await recovery.create_backup("Manual backup before shutdown")
    print(f"Created backup: {backup_id}")
    
    # Shutdown
    print("\nShutting down services...")
    await PersistentServiceFactory.shutdown()
    
    # Phase 2: Simulate crash and recovery
    print("\n\nPhase 2: Simulating crash and recovery\n")
    
    # Re-initialize (simulating application restart)
    await PersistentServiceFactory.initialize()
    library_repo2 = PersistentServiceFactory.get_library_repository()
    
    # Check recovered state
    recovered_count = await library_repo2.count()
    print(f"Libraries recovered: {recovered_count}")
    
    # Verify all libraries
    print("\nVerifying recovered libraries:")
    for original in libraries_created:
        recovered = await library_repo2.get(original.id)
        if recovered:
            print(f"✓ {recovered.name} - Successfully recovered")
            print(f"  Metadata: {recovered.metadata}")
        else:
            print(f"✗ {original.name} - NOT FOUND!")
    
    # Add more data after recovery
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
    await library_repo2.create(new_library)
    print(f"Created: {new_library.name}")
    
    final_count = await library_repo2.count()
    print(f"\nFinal library count: {final_count}")
    
    # Show recovery statistics
    recovery2 = get_recovery_service()
    consistency = await recovery2.verify_consistency()
    print(f"\nSystem consistency: {'✓ Consistent' if consistency['consistent'] else '✗ Inconsistent'}")
    print(f"Stats: {consistency['stats']}")
    
    # Cleanup
    await PersistentServiceFactory.shutdown()
    
    print("\n✓ Persistence example complete!")


if __name__ == "__main__":
    asyncio.run(main())
