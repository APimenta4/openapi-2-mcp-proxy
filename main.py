import os
import asyncio
from mcp.server.fastmcp import FastMCP
from server import run_server
from utils import create_dynamic_function, load_provider_configuration

mcp = FastMCP("Rest API Proxy Server", "1.0.0")

# Scan for specifications subdirectories
subdirectories = [f.path for f in os.scandir("specifications") if f.is_dir()]

if not subdirectories:
    raise Exception("No provider directories found in 'specifications' directory.")

provider_info_dict = dict()
# Read configuration from each provider
for subdir in subdirectories:
    provider_name = os.path.basename(subdir)
    try:   
        # Load provider configuration and save to dictionary
        provider_info = load_provider_configuration(subdir, provider_name)
        provider_info_dict[provider_name] = provider_info
    except FileNotFoundError:
        print(f"Skipping provider {provider_name}: Configuration file not found.")
    except Exception as e:
        print(f"Skipping provider {provider_name}: {e}")

if not provider_info_dict:
    raise Exception("No providers with proper configuration were found.")
    
# for each provided OpenAPI specification
for provider_name, provider_info in provider_info_dict.items():
    specification = provider_info['specification']
    base_url = provider_info['base_url']
    headers = provider_info['headers']
    # for each endpoint
    for path in specification.paths:
        # for each operation (endpoint + method)
        for operation in path.operations:
            try:
                function = create_dynamic_function(provider_name, operation, path, base_url, headers)
                mcp.tool()(function) 
            except Exception as e:
                print(f"Skipping tool creation for {provider_name} - {operation.method.value} {path.url}: {e}")       

if __name__ == "__main__":
    created_tools = asyncio.run(mcp.list_tools())
    print(f"Created {len(created_tools)} tools from {len(provider_info_dict)} providers.")
    for i, tool in enumerate(created_tools):
        print(f"Tool {i+1}: {tool.name}")
    run_server(mcp, 8084)


