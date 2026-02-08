"""MCP tool/resource definitions (informal) for discovery."""

tools = [
    {
        "name": "list_tools",
        "description": "List available tools and their descriptions.",
        "params": {},
    },
    {
        "name": "list_layers",
        "description": "List project layers (id, name, type, crs).",
        "params": {},
    },
    {
        "name": "list_algorithms",
        "description": "List processing algorithms (id, name, provider).",
        "params": {},
    },
    {
        "name": "run_processing",
        "description": "Run a processing algorithm.",
        "params": {
            "algorithm": "string id, e.g., native:buffer",
            "parameters": "object of alg params"
        }
    },
    {
        "name": "run_script",
        "description": "Run sandboxed PyQGIS code with stdout/stderr capture (30s timeout).",
        "params": {
            "code": "Python code string"
        }
    },
    {
        "name": "fetch_log",
        "description": "Fetch stdout/stderr/error by run_id.",
        "params": {
            "run_id": "string"
        }
    }
]

resources = [
    {
        "name": "layers",
        "description": "Current project layers",
        "provider": "list_layers"
    },
    {
        "name": "algorithms",
        "description": "Available processing algorithms",
        "provider": "list_algorithms"
    }
]
