from typing import Any, Dict, Optional, Union, List
from pymongo import MongoClient

class MongoDBManager:
    def __init__(self, mongodb_url: str) -> None:
        """Initialize the MongoDBManager with a connection string."""
        self.client = MongoClient(mongodb_url)

    def set_db_and_collection(self, db_name: str, collection_name: str) -> None:
        """Set the database and collection to use."""
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

    def query(self, query_type: str, **kwargs: Any) -> Optional[Union[List[Dict], int, bool]]:
        """Handle various types of queries on the MongoDB collection.

        Args:
            query_type (str): The type of query to perform. Supported types:
                - "list_all_available_schedulers"
                - "list_all_schedulers"
                - "check_scheduled_tasks"
                - "count_scheduled_tasks"
                - "custom_query"
                - "custom_count"
            **kwargs: Additional arguments for the query.

        Returns:
            Optional[Union[List[Dict], int, bool]]: The result of the query.
        """
        if query_type == "list_all_available_schedulers":
            return [doc["_id"] for doc in self.collection.find({"status": "available"}, projection=["_id"])]
        
        elif query_type == "list_all_schedulers":
            return [doc["_id"] for doc in self.collection.find(projection=["_id"])]
        
        elif query_type == "check_scheduled_tasks":
            return self.collection.count_documents({"status": "scheduled"}) > 0
        
        elif query_type == "count_scheduled_tasks":
            return self.collection.count_documents({"status": "scheduled"})
        
        elif query_type == "custom_query":
            custom_query = kwargs.get("custom_query", {})
            return list(self.collection.find(custom_query))
        
        elif query_type == "custom_count":
            custom_query = kwargs.get("custom_query", {})
            return self.collection.count_documents(custom_query)
        
        else:
            raise ValueError(f"Unsupported query type: {query_type}")

# Example usage:
mongodb_manager = MongoDBManager(mongodb_url="mongodb://localhost:27017/")
mongodb_manager.set_db_and_collection(db_name="Crypto", collection_name="ohclv")

# Perform queries
available_schedulers = mongodb_manager.query("list_all_available_schedulers")
print(available_schedulers)

all_schedulers = mongodb_manager.query("list_all_schedulers")
print(all_schedulers)

has_scheduled_tasks = mongodb_manager.query("check_scheduled_tasks")
print(has_scheduled_tasks)

scheduled_task_count = mongodb_manager.query("count_scheduled_tasks")
print(scheduled_task_count)

# Custom query
#custom_query = {"field": "value"}
#custom_results = mongodb_manager.query("custom_query", custom_query=custom_query)
#print(custom_results)

#custom_count = mongodb_manager.query("custom_count", custom_query=custom_query)
#print(custom_count)

# Switch to a different database and collection
#mongodb_manager.set_db_and_collection(db_name="another_database", collection_name="another_collection")

# Perform queries on the new collection
#new_results = mongodb_manager.query("custom_query", custom_query={"another_field": "another_value"})
#print(new_results)