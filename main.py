from mcp.server.fastmcp import FastMCP
from server import run_server
from openapi_parser import parse
import os
from utils import create_dynamic_function
import json
import asyncio

provider_info_dict = dict()

mcp = FastMCP("Rest API Proxy Server", "1.0.0")

# Scan for specifications subdirectories
subdirectories = [f.path for f in os.scandir("specifications") if f.is_dir()]

if not subdirectories:
    raise Exception("No provider directories found in 'specifications' directory.")

# Read configuration files for each subdirectory
for subdir in subdirectories:
    provider_name = os.path.basename(subdir)
    try:   
        # Parse the OpenAPI specification
        specification = None
        for spec_filename in ['specification.json', 'specification.yaml', 'specification.yml']:
            spec_path = os.path.join(subdir, spec_filename)
            if os.path.exists(spec_path):
                specification = parse(spec_path)
                print(f"Found and parsed {spec_filename} for {provider_name}")
                break
        
        if not specification:
            raise Exception(f"No specification file found.")

        provider_info = {
            'specification': specification
        }
        
        # Load provider-specific configuration file
        config_path = os.path.join(subdir, 'config.json')
        try:
            with open(config_path, 'r') as config_file:
                config = json.load(config_file)
                # Override with configuration if available
                if config:
                    if 'base_url' in config:
                        provider_info['base_url'] = config['base_url']
                    else:
                        raise Exception(f"base_url not found in configuration for {provider_name}.")
                    if 'headers' in config:
                        provider_info['headers'] = config['headers']
            # Add to dictionary
            provider_info_dict[provider_name] = provider_info
        except FileNotFoundError:
            raise Exception(f"Configuration file not found.")
        except Exception as e:
            raise Exception(f"Error loading configuration: {e}")
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
    run_server(mcp, 8090)


