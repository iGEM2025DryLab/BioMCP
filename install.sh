#!/bin/bash
# BioMCP Installation Script
# Supports macOS, Linux, and Windows (via Git Bash/WSL)

set -e  # Exit on error

echo "🧬 BioMCP Installation Script"
echo "==============================="

# Check Python version
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo "❌ Python is not installed. Please install Python 3.10+ first."
        exit 1
    fi
    
    # Check Python version
    PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    REQUIRED_VERSION="3.10"
    
    if [[ $(echo "$PYTHON_VERSION $REQUIRED_VERSION" | awk '{print ($1 >= $2)}') -eq 1 ]]; then
        echo "✅ Python $PYTHON_VERSION detected"
    else
        echo "❌ Python $REQUIRED_VERSION+ required. Found: $PYTHON_VERSION"
        exit 1
    fi
}

# Check if conda is available
check_conda() {
    if command -v conda &> /dev/null; then
        echo "✅ Conda detected"
        return 0
    else
        echo "⚠️  Conda not found. Will use pip instead."
        return 1
    fi
}

# Install with conda
install_conda() {
    echo "📦 Installing with Conda..."
    cd bio_mcp
    
    if conda env list | grep -q "bio_mcp"; then
        echo "📝 Environment 'bio_mcp' already exists. Updating..."
        conda env update -f environment.yml
    else
        echo "🆕 Creating new environment 'bio_mcp'..."
        conda env create -f environment.yml
    fi
    
    echo "✅ Conda environment ready!"
    echo "💡 Activate with: conda activate bio_mcp"
}

# Install with pip
install_pip() {
    echo "📦 Installing with pip..."
    cd bio_mcp
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "🆕 Creating virtual environment..."
        $PYTHON_CMD -m venv venv
    fi
    
    # Activate virtual environment
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        source venv/Scripts/activate
    else
        source venv/bin/activate
    fi
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    echo "📋 Installing requirements..."
    pip install -r requirements.txt
    
    echo "✅ Pip installation complete!"
    echo "💡 Activate with: source venv/bin/activate (Linux/Mac) or venv\\Scripts\\activate (Windows)"
}

# Run tests
run_tests() {
    echo "🧪 Running system tests..."
    cd bio_mcp
    
    if check_conda && conda env list | grep -q "bio_mcp"; then
        conda run -n bio_mcp python test_system.py
    else
        if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
            source venv/Scripts/activate
        else
            source venv/bin/activate
        fi
        python test_system.py
    fi
}

# Main installation
main() {
    echo "🔍 Checking system requirements..."
    check_python
    
    # Choose installation method
    if check_conda; then
        echo "🤔 Choose installation method:"
        echo "1) Conda (recommended)"
        echo "2) Pip"
        read -p "Enter choice (1-2): " choice
        
        case $choice in
            1)
                install_conda
                ;;
            2)
                install_pip
                ;;
            *)
                echo "Invalid choice. Using Conda..."
                install_conda
                ;;
        esac
    else
        install_pip
    fi
    
    # Ask about running tests
    echo ""
    read -p "🧪 Run system tests? (y/n): " run_test
    if [[ $run_test == "y" || $run_test == "Y" ]]; then
        run_tests
    fi
    
    echo ""
    echo "🎉 Installation complete!"
    echo ""
    echo "🚀 Quick start:"
    echo "   cd bio_mcp"
    if check_conda && conda env list | grep -q "bio_mcp"; then
        echo "   conda activate bio_mcp"
    else
        if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
            echo "   source venv/Scripts/activate"
        else
            echo "   source venv/bin/activate"
        fi
    fi
    echo "   python3 bio_mcp.py interactive"
    echo ""
    echo "📖 For detailed documentation, see: bio_mcp/README.md"
}

# Run main function
main "$@"