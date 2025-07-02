@echo off
REM BioMCP Installation Script for Windows
REM Requires Python 3.10+ and optionally Anaconda/Miniconda

echo 🧬 BioMCP Installation Script for Windows
echo ==========================================

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

REM Check Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python %PYTHON_VERSION% detected

REM Change to bio_mcp directory
cd bio_mcp
if %errorlevel% neq 0 (
    echo ❌ Cannot find bio_mcp directory
    pause
    exit /b 1
)

REM Check if conda is available
conda --version >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Conda detected
    echo 🤔 Choose installation method:
    echo 1^) Conda ^(recommended^)
    echo 2^) Pip
    set /p choice="Enter choice (1-2): "
    
    if "!choice!"=="1" (
        goto install_conda
    ) else (
        goto install_pip
    )
) else (
    echo ⚠️  Conda not found. Using pip...
    goto install_pip
)

:install_conda
echo 📦 Installing with Conda...
conda env list | findstr "bio_mcp" >nul
if %errorlevel% equ 0 (
    echo 📝 Environment 'bio_mcp' already exists. Updating...
    conda env update -f environment.yml
) else (
    echo 🆕 Creating new environment 'bio_mcp'...
    conda env create -f environment.yml
)
echo ✅ Conda environment ready!
echo 💡 Activate with: conda activate bio_mcp
goto end

:install_pip
echo 📦 Installing with pip...
if not exist "venv" (
    echo 🆕 Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ❌ Failed to create virtual environment
        pause
        exit /b 1
    )
)

echo 🔄 Activating virtual environment...
call venv\Scripts\activate.bat

echo 📋 Installing requirements...
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ❌ Failed to install requirements
    pause
    exit /b 1
)

echo ✅ Pip installation complete!
echo 💡 Activate with: venv\Scripts\activate.bat

:end
echo.
set /p run_test="🧪 Run system tests? (y/n): "
if /i "!run_test!"=="y" (
    echo 🧪 Running system tests...
    python test_system.py
)

echo.
echo 🎉 Installation complete!
echo.
echo 🚀 Quick start:
echo    cd bio_mcp
echo    venv\Scripts\activate.bat  ^(if using pip^)
echo    conda activate bio_mcp     ^(if using conda^)
echo    python bio_mcp.py interactive
echo.
echo 📖 For detailed documentation, see: bio_mcp\README.md
pause