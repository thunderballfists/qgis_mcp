"""
MCP-style tool and resource definitions (JSON-LD-ish) for discovery.
These are advertised via list_tools and list_resources.
"""

tools = [
    {
        "name": "list_tools",
        "description": "List available tools and their schemas.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_resources",
        "description": "List available resources (layers, algorithms).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_layers",
        "description": "List project layers (id, name, type, crs).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_algorithms",
        "description": "List processing algorithms (id, name, provider).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "run_processing",
        "description": "Run a processing algorithm.",
        "input_schema": {
            "type": "object",
            "properties": {
                "algorithm": {"type": "string"},
                "parameters": {"type": "object"},
                "async": {"type": "boolean", "default": False}
            },
            "required": ["algorithm", "parameters"]
        }
    },
    {
        "name": "run_script",
        "description": "Run sandboxed PyQGIS code with stdout/stderr capture.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "async": {"type": "boolean", "default": False}
            },
            "required": ["code"]
        }
    },
    {
        "name": "fetch_log",
        "description": "Fetch stdout/stderr/error/progress by run_id.",
        "input_schema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"]
        }
    },
    {
        "name": "cancel_run",
        "description": "Cancel a running job by run_id.",
        "input_schema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"]
        }
    }
]

resources = [
    {
        "name": "layers",
        "description": "Current project layers",
        "provider": "list_layers",
        "schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "type": {"type": "integer"},
                    "crs": {"type": "string"}
                }
            }
        }
    },
    {
        "name": "algorithms",
        "description": "Available processing algorithms",
        "provider": "list_algorithms",
        "schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "provider": {"type": "string"}
                }
            }
        }
    }
]
