import inspect
import requests
import os
import json
from typing import Optional
from openapi_parser import parse
from openapi_parser.enumeration import ParameterLocation

class FunctionParameter:
    name: str
    required: bool
    description: Optional[str] = None
    _in: str
    
    def __init__(self, name: str, required: bool, _in: str, description: Optional[str] = None):
        self.name = name
        self.required = required
        self.description = name + " - " + description + f" ({'required' if required else 'optional'})"
        self._in = _in
    
    def to_inspect_parameter(self) -> inspect.Parameter:
        return inspect.Parameter(
            name=self.name,
            kind=inspect.Parameter.KEYWORD_ONLY,
            default=inspect.Parameter.empty if self.required else None
        )

def create_dynamic_function(provider_name, operation, path, base_url, provider_headers):
    """

    """
    parameters = [] 
    # Add parameters associated with operation
    for param in operation.parameters:
        param_name = param.name.replace('-', '_')
        new_parameter = FunctionParameter(
            # Remove invalid characters
            name=''.join(e for e in param_name if e.isalnum() or e == '_'),
            required=param.required,
            description=param.description,
            _in = param.location
        )
        parameters.append(new_parameter)

    # Create function signature
    params_signature_format = []
    for param in parameters:
        params_signature_format.append(param.to_inspect_parameter())
    dynamic_signature = inspect.Signature(parameters=params_signature_format)
    
    # Define the function content
    async def function_implementation(**kwargs):
        method = operation.method.value
        url = base_url + path.url
        headers = provider_headers or {}

        # Prepare the request
        query_params = {}
        for param in parameters:
            # Check if required parameter is present
            if param.required and param.name not in kwargs:
                raise ValueError(f"Required parameter '{param.name}' is missing")
                
            # Skip optional parameters that weren't provided
            if not param.required and param.name not in kwargs:
                continue

            if param._in == ParameterLocation.QUERY:
                query_params[param.name] = kwargs[param.name]
            elif param._in == ParameterLocation.PATH:
                url = url.replace(f"{{{param.name}}}", str(kwargs[param.name]))
            elif param._in == ParameterLocation.HEADER:
                headers[param.name] = kwargs[param.name]

        # Make the request
        try:
            response = requests.request(method, url, headers=headers, params = query_params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return f"Request failed: {e}"
    
    async def dynamic_function(*args, **kwargs):
        # Validate arguments against the signature
        mapped_args = dynamic_signature.bind(*args, **kwargs)
        mapped_args.apply_defaults()
        return await function_implementation(**mapped_args.arguments)
    
    # Set function arguments
    dynamic_function.__signature__ = dynamic_signature
    
    function_name = provider_name + "_" + operation.operation_id
    # Remove invalid characters
    clean_name = ''.join(e for e in function_name if e.isalnum() or e == '_')

    # Set function name 
    dynamic_function.__name__ = clean_name
    
    # Set function docstring
    doc = operation.description or f"Make a {operation.method.value} request to {path.url}"
    if parameters:
        doc += "\nArguments:"
        for param in parameters:
            doc += f"\n{param.description}"
    dynamic_function.__doc__ = doc

    return dynamic_function

def load_provider_configuration(subdir, provider_name):
    # Parse the OpenAPI specification
    specification = None
    for spec_filename in ['specification.json', 'specification.yaml', 'specification.yml']:
        spec_path = os.path.join(subdir, spec_filename)
        if os.path.exists(spec_path):
            specification = parse(spec_path)
            print(f"Found and parsed {spec_filename} for provider {provider_name}.")
            break
    
    if not specification:
        raise Exception(f"No specification file found.")

    provider_info = {
        'specification': specification
    }
    
    # Load provider-specific configuration file
    config_path = os.path.join(subdir, 'config.json')
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
        # Override with configuration if available
        if config:
            if 'base_url' in config:
                provider_info['base_url'] = config['base_url']
            else:
                raise Exception(f"base_url not found in config.json")
            if 'headers' in config:
                provider_info['headers'] = config['headers']
    
    return provider_info