#!/usr/bin/env python3
"""
Data Migration Script

This script migrates data from JSON files to MongoDB collections.
"""

import json
import os
from mongo_db import MongoDB

def migrate_json_to_mongodb():
    """Migrate all JSON files in fake_data directory to MongoDB."""
    print("Starting migration of JSON data to MongoDB...")
    
    # Connect to MongoDB
    db = MongoDB()
    if not db.connect():
        print("Failed to connect to MongoDB. Migration aborted.")
        return False
    
    # Get list of JSON files in fake_data directory
    json_files = [f for f in os.listdir('fake_data') if f.endswith('.json')]
    
    if not json_files:
        print("No JSON files found in fake_data directory.")
        return False
    
    success_count = 0
    
    # Process each JSON file
    for json_file in json_files:
        collection_name = os.path.splitext(json_file)[0]  # Remove .json extension
        file_path = os.path.join('fake_data', json_file)
        
        try:
            # Read JSON data
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Clear existing collection data
            db.delete_many(collection_name, {})
            
            # Insert data into MongoDB
            if isinstance(data, list):
                if data:
                    inserted = db.insert_many(collection_name, data)
                    print(f"Migrated {inserted} documents to '{collection_name}' collection")
                else:
                    print(f"No data to migrate from {json_file}")
            else:
                # For single documents like usage
                db.insert_one(collection_name, data)
                print(f"Migrated document to '{collection_name}' collection")
            
            success_count += 1
            
        except Exception as e:
            print(f"Error migrating {json_file}: {e}")
    
    print(f"Migration completed. Successfully migrated {success_count}/{len(json_files)} files.")
    return success_count > 0

if __name__ == "__main__":
    migrate_json_to_mongodb()