# Bio MCP - AI-Powered Biological Research Platform

Bio MCP is an advanced AI-powered biological research platform that combines Model Context Protocol (MCP) with multiple LLM providers to enable sophisticated biological data analysis, structure visualization, and research workflows.

## 🚀 Features

### Core Capabilities
- **Multi-LLM Support**: Anthropic Claude, OpenAI GPT, Google Gemini, Aliyun Qwen
- **Biological Analysis Tools**: PROPKA for pKa calculations, PyMOL for structure visualization
- **Smart File System**: Context-efficient reading for large biological files
- **MCP Integration**: Model Context Protocol for AI tool interoperability
- **Interactive Interface**: Command-line interface with comprehensive features

### Supported File Types
- **Protein Structures**: PDB, mmCIF
- **Sequences**: FASTA, GenBank
- **Analysis Results**: CSV, JSON, text formats

### Analysis Tools
- **PROPKA**: Protein pKa calculations and ionization analysis
- **PyMOL**: Molecular visualization and structure analysis
- **File Management**: Upload, organize, and analyze biological data files
- **Content Search**: Pattern matching and content extraction

## 📋 Requirements

- Python 3.10 or higher
- Optional: Conda/Miniconda for environment management
- API keys for LLM providers (optional but recommended)

## 🛠️ Installation

### 1. Clone and Setup Environment

```bash
git clone <repository-url>
cd bio_mcp

# Option A: Using conda (recommended)
conda env create -f environment.yml
conda activate bio_mcp

# Option B: Using pip
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install bio analysis tools (optional)
# For PROPKA support
pip install propka

# For PyMOL support (requires separate installation)
# See: https://pymol.org/2/
```

### 3. Configure API Keys (Optional)

Create a `.env` file in the project root:

```bash
# LLM API Keys (add the ones you have)
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here
GOOGLE_API_KEY=your_google_key_here
DASHSCOPE_API_KEY=your_aliyun_key_here
```

## 🎯 Quick Start

### Start the Interactive System (Recommended)

```bash
# Main entry point - start interactive mode
python3 bio_mcp.py interactive

# Alternative - direct host launch  
python3 run_host.py --interactive
```

### Launch Options

```bash
# Interactive mode (recommended)
python3 bio_mcp.py interactive

# Start MCP server only
python3 bio_mcp.py server

# Launch web GUI
python3 bio_mcp.py gui

# Start host application
python3 bio_mcp.py host --interactive
```

### Basic Commands (in interactive mode)

```bash
# System status
bio-mcp> status

# List available tools
bio-mcp> tools

# List LLM clients
bio-mcp> clients

# Upload a biological file
bio-mcp> upload /path/to/protein.pdb

# List uploaded files
bio-mcp> files

# Chat with AI (requires API keys)
bio-mcp> chat analyze this protein structure

# Health check
bio-mcp> health

# Exit
bio-mcp> quit
```

## 📁 Project Structure

```
bio_mcp/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── environment.yml          # Conda environment
├── run_host.py              # Main entry point (host)
├── run_server.py            # MCP server entry point
├── launch_gui.py            # Web GUI launcher
├── .env                     # API keys (create this)
│
├── mcp_host/                # Host application
│   └── bio_mcp_host/
│       ├── host.py          # Main host coordinator
│       ├── llm_manager.py   # LLM client management
│       ├── main.py          # Host entry point
│       ├── llm_clients/     # LLM provider clients
│       └── mcp_client/      # MCP client implementation
│
├── mcp_server/              # MCP server
│   └── bio_mcp_server/
│       ├── main.py          # Server entry point
│       ├── server.py        # MCP server implementation
│       ├── file_system.py   # File management
│       └── tools/           # Analysis tools
│           ├── propka_tool.py
│           └── pymol_tool.py
│
└── bio_data/                # Data storage
    ├── structures/          # Uploaded protein structures
    ├── sequences/           # Uploaded sequences
    ├── analysis/            # Analysis results
    └── visualizations/      # Generated visualizations
```

## 🔧 Advanced Usage

### Programming Interface

```python
from bio_mcp_host.host import BioMCPHost

# Create and start host
host = BioMCPHost(["python3", "run_server.py"])
await host.start()

# Upload file
result = await host.upload_file("protein.pdb")

# Run analysis
pka_result = await host.bio_mcp_client.calculate_pka(
    file_id="protein_123",
    ph=7.0
)

# Chat with AI
async for chunk in host.chat_stream("session_1", "Analyze this protein"):
    print(chunk, end="")
```

### Web Interface

```bash
# Launch web GUI (preferred method)
python3 bio_mcp.py gui

# Alternative direct launch
python3 launch_gui.py

# Open browser to http://localhost:8000
```

## 🧪 Testing

Test the complete system:

```bash
# Test entire Bio MCP system
python3 test_system.py
```

## 🛡️ Architecture

### Model Context Protocol (MCP)
Bio MCP uses the Model Context Protocol for AI tool interoperability. The system implements a direct JSON-RPC client that bypasses potential SDK stdio transport issues for maximum reliability.

### Multi-LLM Architecture
- **Unified Interface**: Single API for multiple LLM providers
- **Automatic Fallback**: Graceful degradation when providers are unavailable
- **Streaming Support**: Real-time response streaming
- **Context Management**: Efficient context window management

### Security Features
- **No Credential Storage**: API keys from environment variables only
- **Sandboxed Execution**: Isolated tool execution
- **Input Validation**: Comprehensive input sanitization

## ⚠️ Troubleshooting

### Common Issues

**MCP Connection Timeout**
- The system uses a direct JSON-RPC implementation to avoid stdio transport issues
- If problems persist, check Python environment and dependencies

**LLM API Errors**
- Verify API keys in `.env` file
- Check API quotas and billing status
- Test individual clients with `clients` command

**Tool Installation Issues**
- PROPKA: `pip install propka`
- PyMOL: Requires separate installation from https://pymol.org/

### Getting Help

1. Run `health` command to check system status
2. Use `status` command to see component availability
3. Check the troubleshooting section in the web GUI

## 🤝 Contributing

This project is designed for biological research applications. When contributing:

1. Maintain security best practices
2. Follow Python coding standards
3. Test thoroughly with biological data
4. Document new features comprehensively

## 📄 License

This project is for research and educational use. Please respect API terms of service for LLM providers.

## 🔗 Related Projects

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [PROPKA](https://github.com/jensengroup/propka)
- [PyMOL](https://pymol.org/)

---

**Bio MCP** - Bridging AI and Biological Research 🧬🤖