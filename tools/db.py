#!/usr/bin/env python3
"""
Database Tools - OpenSearch and database connectivity tools

Demonstrates database integration patterns with proper error handling.
"""
import asyncio
# Force fresh import
import importlib
import sys
from typing import Any, Dict, Optional

sys.path.append("..")
from base_tool import ToolError, ToolResult
# Clear any cached registrations
from tool_decorators import (MethodToolRegistry, clear_decorator_registry,
                             tool, tool_method)

clear_decorator_registry()


@tool("opensearch", "Search and retrieve regulation documents - use this tool when user asks to search, find, or get documents")
async def search_regulations(
    query: Dict[str, Any], index: str = "regulations", size: int = 10
) -> ToolResult:
    """
    Search for regulations documents in OpenSearch. Use this tool when users want to search for, find, or retrieve regulation documents.

    Args:
        query: OpenSearch query object. For general document searches use {'query': {'match_all': {}}}. For specific searches use {'query': {'match': {'content': 'search terms'}}}. When user asks for "regulation documents" or "my documents" without specific terms, use match_all query.

        index: Database index name (default: regulations). Available: regulations, policies, guidelines, standards

        size: Number of results to return (default: 10, max: 100)

    Returns:
        ToolResult containing search results with document metadata, scores, and highlights.
    """
    
    # If query is empty or user asks for general documents, default to match_all
    if not query or (isinstance(query, dict) and not query):
        query = {"query": {"match_all": {}}}
    
    # If user provides simple string, convert to proper query
    if isinstance(query, str):
        query = {"query": {"match": {"content": query}}}

    # Mock OpenSearch response (replace with actual OpenSearch client)
    result = ToolResult()
    mock_response = {
        "took": 5,
        "timed_out": False,
        "hits": {
            "total": {"value": 2, "relation": "eq"},
            "hits": [
                {
                    "_id": "reg001",
                    "_source": {
                        "title": "GDPR Compliance Guidelines",
                        "content": "General Data Protection Regulation compliance requirements...",
                        "category": "privacy",
                        "effective_date": "2018-05-25",
                    },
                    "_score": 0.95,
                },
                {
                    "_id": "reg002",
                    "_source": {
                        "title": "Data Processing Standards",
                        "content": "Standards for processing personal data in compliance...",
                        "category": "data-protection",
                        "effective_date": "2018-05-25",
                    },
                    "_score": 0.87,
                },
            ],
        },
    }

    result.add_json(mock_response)

    result.add_json(
        {
            "query": query,
            "results": mock_response["hits"]["hits"],
            "total": mock_response["hits"]["total"]["value"],
        }
    )

    return result


class DatabaseTools:
    """Collection of database utility tools"""

    @tool_method("db_health", "Check database connection health")
    async def check_db_health(self, database: str = "opensearch") -> ToolResult:
        """Check if database connection is healthy"""
        result = ToolResult()

        # Mock health check (replace with actual DB ping)
        if database == "opensearch":
            health_status = {
                "status": "green",
                "cluster_name": "regulations-cluster",
                "number_of_nodes": 3,
                "active_primary_shards": 15,
                "active_shards": 30,
                "unassigned_shards": 0,
            }

            result.add_text(f"🏥 {database.title()} Health Check")
            result.add_text(f"   Status: {health_status['status'].upper()} ✅")
            result.add_text(f"   Cluster: {health_status['cluster_name']}")
            result.add_text(f"   Nodes: {health_status['number_of_nodes']}")
            result.add_text(f"   Active Shards: {health_status['active_shards']}")

        else:
            result.add_text(f"❌ Unknown database: {database}")
            result.add_text("   Supported: opensearch")

        return result

    @tool_method("list_indices", "List available database indices")
    async def list_indices(self, pattern: str = "*") -> ToolResult:
        """List available indices matching pattern"""
        result = ToolResult()

        # Mock indices list (replace with actual DB query)
        mock_indices = [
            {"name": "regulations", "docs": 1250, "size": "2.1mb"},
            {"name": "policies", "docs": 890, "size": "1.5mb"},
            {"name": "guidelines", "docs": 450, "size": "800kb"},
            {"name": "standards", "docs": 320, "size": "600kb"},
        ]

        # Filter by pattern (simple wildcard matching)
        if pattern != "*":
            filtered_indices = [
                idx for idx in mock_indices if pattern.lower() in idx["name"].lower()
            ]
        else:
            filtered_indices = mock_indices

        result.add_text(f"📚 Database Indices (pattern: '{pattern}')")
        result.add_text(f"   Found: {len(filtered_indices)} indices")

        for idx in filtered_indices:
            result.add_text(f"   📖 {idx['name']}: {idx['docs']} docs, {idx['size']}")

        result.add_json({"indices": filtered_indices, "pattern": pattern})

        return result

    @tool_method("create_query", "Build a database query")
    async def build_query(
        self,
        search_terms: str,
        filters: Optional[str] = None,
        sort_by: str = "relevance",
    ) -> ToolResult:
        """Build a properly formatted database query"""
        result = ToolResult()

        # Build query structure
        query_structure = {
            "query": {"bool": {"must": [{"match": {"content": search_terms}}]}},
            "sort": [],
        }

        # Add filters if provided
        if filters:
            filter_terms = filters.split(",")
            for filter_term in filter_terms:
                if ":" in filter_term:
                    field, value = filter_term.strip().split(":", 1)
                    query_structure["query"]["bool"]["filter"] = [
                        {"term": {field.strip(): value.strip()}}
                    ]

        # Add sorting
        if sort_by == "date":
            query_structure["sort"] = [{"effective_date": {"order": "desc"}}]
        elif sort_by == "relevance":
            query_structure["sort"] = ["_score"]

        result.add_text(f"🔧 Query Builder")
        result.add_text(f"   Search terms: '{search_terms}'")
        if filters:
            result.add_text(f"   Filters: {filters}")
        result.add_text(f"   Sort by: {sort_by}")

        result.add_text(f"\n📄 Generated Query:")
        result.add_json(query_structure)

        return result


# Register method-based tools
MethodToolRegistry.register_class_methods(DatabaseTools())


# Test function for development
async def test_db_tools():
    """Test database tools during development"""
    print("🧪 Testing Database Tools")

    # Test function tool
    search_result = await search_regulations("GDPR compliance", "regulations", 5)
    print(f"Search result: {search_result.to_dict()}")

    # Test method tools
    db_tools = DatabaseTools()
    health_result = await db_tools.check_db_health("opensearch")
    print(f"Health result: {health_result.to_dict()}")


if __name__ == "__main__":
    asyncio.run(test_db_tools())
