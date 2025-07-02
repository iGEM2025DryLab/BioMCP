# BioMCP - AI-Powered Biological Research Platform

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

BioMCP is an advanced AI-powered biological research platform that combines Model Context Protocol (MCP) with multiple LLM providers to enable sophisticated biological data analysis, structure visualization, and research workflows.

## 🚀 Features

- **Multi-LLM Support**: Anthropic Claude, OpenAI GPT, Google Gemini, Aliyun Qwen
- **Biological Analysis Tools**: PROPKA for pKa calculations, PyMOL for structure visualization
- **Smart File System**: Context-efficient reading for large biological files
- **MCP Integration**: Model Context Protocol for AI tool interoperability
- **Cross-Platform**: Works on Windows, macOS, and Linux

## 📋 Requirements

- Python 3.10 or higher
- Optional: Conda/Miniconda for environment management
- API keys for LLM providers (optional but recommended for AI features)

## 🛠️ Installation

### Quick Start

```bash
git clone <repository-url>
cd BioMCP/bio_mcp

# Option A: Using conda (recommended)
conda env create -f environment.yml
conda activate bio_mcp

# Option B: Using pip
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run the system
python3 bio_mcp.py interactive
```

### Detailed Setup

See the [bio_mcp/README.md](bio_mcp/README.md) for comprehensive installation and usage instructions.

## 🎯 Usage

### Interactive Mode (Recommended)
```bash
cd bio_mcp
python3 bio_mcp.py interactive
```

### Available Commands
- `status` - Show system status
- `tools` - List available tools
- `clients` - List LLM clients
- `upload <file>` - Upload biological files
- `chat <message>` - Chat with AI
- `health` - Health check

## 🧪 Testing

```bash
cd bio_mcp
python3 test_system.py
```

## 📁 Project Structure

```
BioMCP/
├── README.md              # This overview
├── .gitignore             # Git ignore rules
└── bio_mcp/               # Main application
    ├── README.md          # Detailed documentation
    ├── requirements.txt   # Python dependencies
    ├── environment.yml    # Conda environment
    ├── bio_mcp.py         # Main entry point
    ├── mcp_host/          # Host application
    ├── mcp_server/        # MCP server
    └── bio_data/          # Data storage
```

## 🤝 Contributing

This project is designed for biological research applications. Please:
1. Maintain security best practices
2. Follow Python coding standards
3. Test thoroughly with biological data
4. Document new features

## 📄 License

This project is for research and educational use. Please respect API terms of service for LLM providers.

## 🔗 Links

- [Detailed Documentation](bio_mcp/README.md)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [PROPKA](https://github.com/jensengroup/propka)
- [PyMOL](https://pymol.org/)