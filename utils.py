import inspect
import requests
import os
import json
from typing import NamedTuple, Optional
from openapi_parser import parse
from openapi_parser.specification import Specification, Operation, Path
from openapi_parser.enumeration import ParameterLocation

class ProviderInformation(NamedTuple):
    """
    A named tuple to hold provider information including OpenAPI specification, base URL, and headers.

    Attributes:
        specification (Specification): The OpenAPI specification object parsed from the specification file.
        base_url (str): The base URL for the API parsed from config file.
        headers (Optional[dict[str, str]]): Headers to be used in the request parsed from config file.
    """
    specification: Specification
    base_url: str
    headers: Optional[dict[str, str]]

class FunctionParameter:
    """
    A class to represent a parameter to be passed to the dynamic function.

    Attributes:
        name (str): The name of the parameter.
        required (bool): Indicates if the parameter is required.
        description (str): A computed description of the parameter.
        _in (ParameterLocation): The location of the parameter. Supports "query", "path" or "header".
    """
    name: str
    required: bool
    description: str
    _in: ParameterLocation
    
    def __init__(self, name: str, required: bool, _in: ParameterLocation, description: str):
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

def create_dynamic_function(provider_name: str, operation: Operation, path: Path, base_url: str, provider_headers: dict[str, str]) -> callable:
    """
    Create a dynamic function that makes an API request 
    based on the information from the OpenAPI specification.

    Args:
        provider_name (str): The name of the provider.
        operation (Operation): The OpenAPI operation object.
        path (Path): The OpenAPI path object.
        base_url (str): The base URL for the API.
        provider_headers (dict): Headers to be used in the request.

    Returns:
        function: A dynamically created function that makes an API request.
    """
    parameters: list[FunctionParameter] = []
    # Add parameters associated with operation
    for param in operation.parameters:
        param_name= param.name.replace('-', '_')
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
    doc = operation.description
    if parameters:
        doc += "\nArguments:"
        for param in parameters:
            doc += f"\n{param.description}"
    dynamic_function.__doc__ = doc

    return dynamic_function

def load_provider_configuration(subdir: str, provider_name: str) -> ProviderInformation:
    """
    Loads the provider's OpenAPI specification, base URL, and headers from the configuration file.
    The configuration file should be named 'config.json' and should contain the following keys:
    - base_url: The base URL for the API.
    - headers: A nested object of headers to be used in the request.

    Args:
        subdir (str): The path to the provider's directory.
        provider_name (str): The name of the provider.
    Returns:
        ProviderInformation: A named tuple containing the OpenAPI specification, base URL, and headers.
    """
    # Parse the OpenAPI specification
    specification = None
    for spec_filename in ['specification.json', 'specification.yaml', 'specification.yml']:
        spec_path = os.path.join(subdir, spec_filename)
        if os.path.exists(spec_path):
            # Parse and validate the specification. Raises an error if invalid
            specification = parse(spec_path)
            print(f"Found and parsed {spec_filename} for provider {provider_name}.")
            break
    
    if not specification:
        raise Exception(f"No specification file found.")

    # Load provider-specific configuration file
    config_path = os.path.join(subdir, 'config.json')
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
        # Override with configuration if available
        if config:
            if 'base_url' in config:
                base_url = config['base_url']
            else:
                raise Exception(f"base_url not found in config.json")
            if 'headers' in config:
                headers = config['headers']
    
    return ProviderInformation(
        specification=specification,
        base_url=base_url,
        headers=headers
    )