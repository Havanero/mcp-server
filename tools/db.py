#!/usr/bin/env python3
"""
Database Tools - OpenSearch and database connectivity tools

Demonstrates database integration patterns with proper error handling.
"""
import asyncio
import sys
from typing import Any, Dict, Optional

sys.path.append("..")
from base_tool import ToolError, ToolResult
from tool_decorators import MethodToolRegistry, tool, tool_method


@tool("opensearch", "Search regulations documents from OpenSearch")
async def search_regulations(
    query: dict, index: str = "regulations", size: int = 10
) -> ToolResult:
    """
    Search for regulations documents in OpenSearch.

    Args:
        query: OpenSearch query dictionary. REQUIRED. Must be a valid OpenSearch query object.
               Examples:
               - Simple text search: {"match": {"content": "GDPR compliance"}}
               - Multi-field search: {"multi_match": {"query": "data protection", "fields": ["title", "content"]}}
               - Boolean search: {"bool": {"must": [{"match": {"content": "privacy"}}, {"term": {"category": "regulation"}}]}}
               - Wildcard search: {"wildcard": {"title": "*data*"}}
               - Range search: {"range": {"effective_date": {"gte": "2020-01-01"}}}
               For user queries like "search for X", convert to: {"match": {"content": "X"}}

        index: Database index or collection name (default: regulations)
               Available indices: regulations, policies, guidelines, standards

        size: Number of results to return (default: 10, max: 100)

    Returns:
        ToolResult containing search results with document metadata, scores, and highlights.
    """

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
