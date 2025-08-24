#!/usr/bin/env python3
"""
MongoDB Connection Module

This module provides functionality to connect to MongoDB and perform CRUD operations
for the OpenStack fake data.
"""

import os
from pymongo import MongoClient
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection settings
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("MONGO_DB_NAME", "openstack_fake_data")

class MongoDB:
    """MongoDB connection and operations class."""
    
    def __init__(self):
        """Initialize MongoDB connection."""
        self.client = None
        self.db = None
        self.connect()
    
    def connect(self) -> bool:
        """Connect to MongoDB database."""
        try:
            self.client = MongoClient(MONGO_URI)
            self.db = self.client[DB_NAME]
            # Ping the database to verify connection
            self.client.admin.command('ping')
            print(f"Connected to MongoDB at {MONGO_URI}")
            return True
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")
            return False
    
    def get_collection(self, collection_name: str):
        """Get a collection by name."""
        if not self.db:
            if not self.connect():
                return None
        return self.db[collection_name]
    
    def find_all(self, collection_name: str) -> List[Dict[str, Any]]:
        """Find all documents in a collection."""
        collection = self.get_collection(collection_name)
        if not collection:
            return []
        return list(collection.find({}, {'_id': 0}))
    
    def find_one(self, collection_name: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single document in a collection."""
        collection = self.get_collection(collection_name)
        if not collection:
            return None
        result = collection.find_one(query, {'_id': 0})
        return result
    
    def insert_one(self, collection_name: str, document: Dict[str, Any]) -> Optional[str]:
        """Insert a document into a collection."""
        collection = self.get_collection(collection_name)
        if not collection:
            return None
        result = collection.insert_one(document)
        return str(result.inserted_id) if result.acknowledged else None
    
    def insert_many(self, collection_name: str, documents: List[Dict[str, Any]]) -> int:
        """Insert multiple documents into a collection."""
        collection = self.get_collection(collection_name)
        if not collection:
            return 0
        result = collection.insert_many(documents)
        return len(result.inserted_ids) if result.acknowledged else 0
    
    def update_one(self, collection_name: str, query: Dict[str, Any], update: Dict[str, Any]) -> bool:
        """Update a single document in a collection."""
        collection = self.get_collection(collection_name)
        if not collection:
            return False
        result = collection.update_one(query, {'$set': update})
        return result.modified_count > 0
    
    def delete_one(self, collection_name: str, query: Dict[str, Any]) -> bool:
        """Delete a single document from a collection."""
        collection = self.get_collection(collection_name)
        if not collection:
            return False
        result = collection.delete_one(query)
        return result.deleted_count > 0
    
    def delete_many(self, collection_name: str, query: Dict[str, Any]) -> int:
        """Delete multiple documents from a collection."""
        collection = self.get_collection(collection_name)
        if not collection:
            return 0
        result = collection.delete_many(query)
        return result.deleted_count
    
    def drop_collection(self, collection_name: str) -> bool:
        """Drop an entire collection."""
        if not self.db:
            return False
        try:
            self.db.drop_collection(collection_name)
            return True
        except Exception as e:
            print(f"Error dropping collection {collection_name}: {e}")
            return False