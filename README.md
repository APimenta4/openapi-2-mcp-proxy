# 🌐 OPENAPI TO MCP PROXY

A dynamic MCP proxy server that automatically creates tools from multiple different local OpenAPI specifications.

## 🚀 Overview

This project creates a proxy MCP server that dynamically generates callable **MCP tools** based on **OpenAPI specifications**. It scans for specifications from different **providers** in the **specifications** directory and makes them available as tools through a FastMCP server.

## ✨ Features

- 🔄 Automatic tool generation from OpenAPI specifications
- 🔌 Support for multiple different API providers
- 🔐 Custom header and authentication support for API authentication
- 🛣️ Handles different parameter locations (query, path, header)
- 🖥️ Flexible server deployment (STDIO or SSE)

## 📋 Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt`
- Validated OpenAPI specifications (suggestion: check with https://editor.swagger.io)

## 🔧 Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd openapi-2-mcp-proxy
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   # On Linux/MacOs:
   source .venv/bin/activate  
   # On Windows:
   .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up each desired API provider configuration.

   Place in the `specifications/{ProviderName}/` directory:

    - An OpenAPI specification file (`specification.json`, `specification.yaml` or `specification.yml`)
    - A `config.json` file with `base_url` and optional `headers` (you should setup authentication here)

## 📁 Project Structure

```
openapi-2-mcp-proxy/
├── main.py                     # ▶️ Main entry point
├── server.py                   # ⚙️ Server setup and configuration
├── utils.py                    # 📙 Utility functions and classes
├── specifications/             # 📂API specifications directory
│   ├── ExampleProvider/ 
│   │   ├── specification.yaml
│   │   └── config.json
│   ├── AnotherProvider/ 
│   │   ├── specification.yaml
│   │   └── config.json
│   ├── .../ 
└── README.md                   # ⬅️ This file
```

## 🚀 Usage

Run the server with SSE (default):
```bash
python main.py
```

Run the server with STDIO:
```bash
python main.py --stdio
```

Customize the host and port:
```bash
python main.py --host 127.0.0.1 --port 9000
```

## 📝 Adding a New API Provider

1. Create a new directory in `specifications/` with your provider name
2. Add an OpenAPI specification file (`specification.json`, `specification.yaml` or `specification.yml`)
3. Create a `config.json` file with the following structure:

   ```json
   {
     "base_url": "https://api.example.com",
     "headers": {
       "Authorization": "Bearer YOUR_TOKEN",  (or a different authentication method)
       "Content-Type": "application/json"
     }
   }
   ```

## ❗ Relevant OpenAPI Specification Fields ❗

The following OpenAPI specification fields are crucial when used by this tool:

```
OpenAPI Specification
...
├── paths                         
│   └── /endpoint/{path_param}       # ❗ Each path becomes a tool
│       ├── [method]                 # ❗ HTTP method (get, post, put, patch, delete, head, options)
│       │   ├── operationId          # ❗ Used as as the name for the tool
│       │   ├── description          # ❗ Used as as the description for the tool
│       │   ├── parameters          
│       │   │   ├── name             # ❗ Argument name
│       │   │   │   ├── in           # ❗ Parameter location (query, path, header)
│       │   │   │   ├── required     # ❗ Whether parameter is mandatory (true, false)
│       │   │   │   └── description  # ❗ Used in the tool description
│       │   │   └── ...    
│       │   └── ...
│       ├── [method]
│       └── ...
└── ...
```

### Used Fields
- **paths**: 
   - **operation** (path + method): Starting point for the MCP Tool to be created
      - **operationId**: Used to generate unique function names for each tool
      - **description** : ⚠️ Description passed as guidelines to the AI Agents. Must clearly include what the tool does and when/how to use it  
      - **parameters**: Defines the arguments the tool is gonna require
         - **name**: Argument name to be used
         - **in**: Determines how the parameter is sent to the API (`query`, `path`, `header`)
         - **required**: Determines if the parameter must be provided to the tool
         - **description**: ⚠️ Used in the tool description. Must clearly indicate what the argument is

### Not Currently Used
- "info" and "servers" fields
- Base urls or authentication setup (use config.json instead)
- Response schemas
- Remaining fields not mentioned here

