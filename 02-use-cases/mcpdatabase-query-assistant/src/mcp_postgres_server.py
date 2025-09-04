#!/usr/bin/env python3
"""
Database MCP Server entry point for Bedrock AgentCore Runtime
"""

import os
import sys
import json
import logging
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

# Load environment variables for database from AWS Secrets Manager first, then config file
def load_database_config():
    """Load database configuration from AWS Secrets Manager, fallback to environment variables"""
    
    # Try AWS Secrets Manager first for database related setup
    try:
        secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        response = secrets_client.get_secret_value(SecretId='mcp-database-credentials')
        secret_data = json.loads(response['SecretString'])
        
        # Set environment variables from secrets
        for key, value in secret_data.items():
            os.environ[key] = str(value)
        
        print(f"Loaded database configuration from AWS Secrets Manager")
        return True
        
    except ClientError as e:
        print(f"Could not retrieve secret from AWS Secrets Manager: {e}")
    except Exception as e:
        print(f"Error accessing AWS Secrets Manager: {e}")
    
    # Fallback to dotenv file loading
    try:
        from dotenv import load_dotenv
        # Try multiple possible paths for database.env (prioritize src/config)
        possible_paths = [
            Path(__file__).parent / "config" / "database.env",  # src/config/database.env (preferred)
            Path(__file__).parent.parent / "config" / "database.env",  # config/database.env (fallback)
            Path("/app/config/database.env"),  # Container absolute path
        ]
        
        config_loaded = False
        for config_path in possible_paths:
            if config_path.exists():
                load_dotenv(config_path)
                print(f"Loaded database configuration from {config_path}")
                config_loaded = True
                break
        
        if not config_loaded:
            print("Database config file not found, using environment variables only")
        
        return config_loaded
        
    except ImportError:
        print("python-dotenv not available, using environment variables only")
        return False

# Load database configuration
load_database_config()

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.fastmcp import FastMCP
from config.mcp_server_config import DatabaseConfig
from mcp_postgres_server_tools import DatabaseTools

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server for AgentCore Runtime compatibility
mcp = FastMCP(host="0.0.0.0", stateless_http=True)

# Load database configuration
db_config = DatabaseConfig.from_env()
db_tools = DatabaseTools(db_config)

# Listing MCP tools

@mcp.tool()
# amazonq-ignore-next-line
def execute_query(query: str) -> dict:
    """Execute a SQL query and return the results."""
    # Basic input validation to prevent obvious SQL injection attempts
    if not query or not query.strip():
        return {"success": False, "error": "Query cannot be empty", "error_type": "validation_error"}
    
    # Block dangerous SQL commands
    dangerous_keywords = ['DROP DATABASE', 'CREATE USER', 'ALTER USER', 'GRANT', 'REVOKE']
    query_upper = query.upper()
    for keyword in dangerous_keywords:
        if keyword in query_upper:
            return {"success": False, "error": f"Dangerous operation '{keyword}' not allowed", "error_type": "security_error"}
    
    return db_tools.execute_query(query)

@mcp.tool()
def list_tables() -> dict:
    """List all tables in the current database."""
    return db_tools.list_tables()

@mcp.tool()
def describe_table(table_name: str, schema_name: str = "public") -> dict:
    """Get detailed information about a specific table."""
    return db_tools.describe_table(table_name, schema_name)

@mcp.tool()
def get_table_stats(table_name: str, schema_name: str = "public") -> dict:
    """Get statistics about a table."""
    query = f"""
    SELECT 
        COUNT(*) as row_count,
        pg_size_pretty(pg_total_relation_size('{schema_name}.{table_name}')) as total_size,
        pg_size_pretty(pg_relation_size('{schema_name}.{table_name}')) as table_size
    FROM {schema_name}.{table_name}
    """
    return db_tools.execute_query(query)

@mcp.tool()
def create_table(table_name: str, columns: str, schema_name: str = "public") -> dict:
    """Create a new table with specified columns."""
    # amazonq-ignore-next-line
    query = f"CREATE TABLE {schema_name}.{table_name} ({columns})"
    return db_tools.execute_query(query)

@mcp.tool()
# amazonq-ignore-next-line
def drop_table(table_name: str, schema_name: str = "public", cascade: bool = False) -> dict:
    """Drop a table from the database."""
    cascade_clause = "CASCADE" if cascade else "RESTRICT"
    query = f"DROP TABLE {schema_name}.{table_name} {cascade_clause}"
    return db_tools.execute_query(query)

@mcp.tool()
# amazonq-ignore-next-line
def insert_data(table_name: str, data: str, schema_name: str = "public") -> dict:
    """Insert data into a table using JSON format."""
    import json
    try:
        data_dict = json.loads(data)
        columns = list(data_dict.keys())
        values = list(data_dict.values())
        
        columns_str = ", ".join(columns)
        placeholders = ", ".join([f"'{v}'" if isinstance(v, str) else str(v) for v in values])
        
        query = f"INSERT INTO {schema_name}.{table_name} ({columns_str}) VALUES ({placeholders})"
        return db_tools.execute_query(query)
        
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Invalid JSON data: {e}",
            "error_type": "json_error"
        }

@mcp.tool()
def update_data(table_name: str, set_clause: str, where_clause: str, schema_name: str = "public") -> dict:
    """Update data in a table."""
    # amazonq-ignore-next-line
    query = f"UPDATE {schema_name}.{table_name} SET {set_clause} WHERE {where_clause}"
    return db_tools.execute_query(query)

@mcp.tool()
# amazonq-ignore-next-line
def delete_data(table_name: str, where_clause: str, schema_name: str = "public") -> dict:
    """Delete data from a table."""
    query = f"DELETE FROM {schema_name}.{table_name} WHERE {where_clause}"
    return db_tools.execute_query(query)

@mcp.tool()
def get_database_info() -> dict:
    """Get general information about the database."""
    return db_tools.get_database_info()

@mcp.tool()
def health_check() -> dict:
    """Health check endpoint to verify the MCP server is running."""
    return db_tools.health_check()

@mcp.tool()
def list_available_tools() -> dict:
    """List all available tools in this MCP server with their descriptions and schemas."""
    tools = [
        {
            "name": "execute_query",
            "description": "Execute a SQL query and return the results",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The SQL query to execute"}
                },
                "required": ["query"]
            }
        },
        {
            "name": "list_tables",
            "description": "List all tables in the current database",
            "inputSchema": {"type": "object", "properties": {}, "required": []}
        },
        {
            "name": "describe_table",
            "description": "Get detailed information about a specific table",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "table_name": {"type": "string", "description": "Name of the table to describe"},
                    "schema_name": {"type": "string", "description": "Schema name (defaults to 'public')"}
                },
                "required": ["table_name"]
            }
        },
        {
            "name": "get_table_stats",
            "description": "Get statistics about a table",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "table_name": {"type": "string", "description": "Name of the table"},
                    "schema_name": {"type": "string", "description": "Schema name (defaults to 'public')"}
                },
                "required": ["table_name"]
            }
        },
        {
            "name": "create_table",
            "description": "Create a new table with specified columns",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "table_name": {"type": "string", "description": "Name of the table to create"},
                    "columns": {"type": "string", "description": "Column definitions (e.g., 'id SERIAL PRIMARY KEY, name VARCHAR(100)')"},
                    "schema_name": {"type": "string", "description": "Schema name (defaults to 'public')"}
                },
                "required": ["table_name", "columns"]
            }
        },
        {
            "name": "drop_table",
            "description": "Drop a table from the database",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "table_name": {"type": "string", "description": "Name of the table to drop"},
                    "schema_name": {"type": "string", "description": "Schema name (defaults to 'public')"},
                    "cascade": {"type": "boolean", "description": "Whether to cascade the drop (defaults to false)"}
                },
                "required": ["table_name"]
            }
        },
        {
            "name": "insert_data",
            "description": "Insert data into a table using JSON format",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "table_name": {"type": "string", "description": "Name of the table"},
                    "data": {"type": "string", "description": "JSON string with data to insert"},
                    "schema_name": {"type": "string", "description": "Schema name (defaults to 'public')"}
                },
                "required": ["table_name", "data"]
            }
        },
        {
            "name": "update_data",
            "description": "Update data in a table",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "table_name": {"type": "string", "description": "Name of the table"},
                    "set_clause": {"type": "string", "description": "SET clause (e.g., 'name = \\'John\\', age = 30')"},
                    "where_clause": {"type": "string", "description": "WHERE clause (e.g., 'id = 1')"},
                    "schema_name": {"type": "string", "description": "Schema name (defaults to 'public')"}
                },
                "required": ["table_name", "set_clause", "where_clause"]
            }
        },
        {
            "name": "delete_data",
            "description": "Delete data from a table",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "table_name": {"type": "string", "description": "Name of the table"},
                    "where_clause": {"type": "string", "description": "WHERE clause (e.g., 'id = 1')"},
                    "schema_name": {"type": "string", "description": "Schema name (defaults to 'public')"}
                },
                "required": ["table_name", "where_clause"]
            }
        },
        {
            "name": "get_database_info",
            "description": "Get general information about the database",
            "inputSchema": {"type": "object", "properties": {}, "required": []}
        },
        {
            "name": "health_check",
            "description": "Health check endpoint to verify the MCP server is running",
            "inputSchema": {"type": "object", "properties": {}, "required": []}
        },
        {
            "name": "list_available_tools",
            "description": "List all available tools in this MCP server with their descriptions and schemas",
            "inputSchema": {"type": "object", "properties": {}, "required": []}
        }
    ]
    
    return {
        "success": True,
        "tools": tools,
        "count": len(tools),
        "message": f"Found {len(tools)} available tools"
    }

if __name__ == "__main__":
    logger.info("Starting Database MCP Server for AgentCore Runtime")
    logger.info(f"Database configuration: {db_config.to_dict()}")
    logger.info("Server will run on 0.0.0.0:8000 with MCP endpoint at /mcp")
    logger.info("Available tools: 12 database management tools")
    
    try:
        mcp.run(transport="streamable-http")
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        db_tools.close_connection()
