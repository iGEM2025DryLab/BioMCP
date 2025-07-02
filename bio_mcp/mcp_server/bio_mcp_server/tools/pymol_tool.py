import os
import tempfile
import subprocess
import asyncio
import base64
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import time

# Modern PyMOL remote control
try:
    from pymol_remote.client import PymolSession
    PYMOL_REMOTE_AVAILABLE = True
except ImportError:
    PYMOL_REMOTE_AVAILABLE = False

class PyMOLTool:
    """PyMOL integration for structure visualization"""
    
    def __init__(self):
        # Find the correct project root directory
        current_file = Path(__file__).resolve()
        project_root = current_file.parent
        
        # Navigate up to find bio_data directory
        while project_root != project_root.parent:
            if (project_root / "bio_data").exists():
                break
            if project_root.name == "bio_mcp":
                break
            project_root = project_root.parent
        
        # Set up directories
        self.bio_data_dir = project_root / "bio_data"
        self.visualization_dir = self.bio_data_dir / "visualizations"
        self.visualization_dir.mkdir(parents=True, exist_ok=True)
        
        # Keep temp dir for script files only
        self.temp_dir = Path(tempfile.gettempdir()) / "bio_mcp_pymol"
        self.temp_dir.mkdir(exist_ok=True)
        
        # PyMOL configuration
        self.pymol_executable = 'pymol'  # Default value
        self.pymol_gui_process = None  # For GUI mode
        
        # Modern pymol_remote configuration
        self.pymol_remote_session = None  # PymolSession for real-time control
        self.pymol_remote_port = 9123  # Default pymol_remote port
        self.pymol_remote_host = "localhost"
        
        # Check PyMOL availability
        self.pymol_available = self._check_pymol_available()
        self.pymol_remote_available = PYMOL_REMOTE_AVAILABLE
        
        # Debug: Store import error for diagnostics
        self.pymol_remote_import_error = None
        if not self.pymol_remote_available:
            try:
                from pymol_remote.client import PymolSession
            except ImportError as e:
                self.pymol_remote_import_error = str(e)
    
    def _check_pymol_available(self) -> bool:
        """Check if PyMOL is available"""
        # Check for environment variable override
        env_pymol_path = os.getenv('PYMOL_EXECUTABLE')
        if env_pymol_path and Path(env_pymol_path).exists():
            self.pymol_executable = env_pymol_path
            return True
            
        # First try to import pymol as a Python module (preferred for conda environments)
        try:
            import pymol
            self.use_pymol_module = True
            return True
        except ImportError:
            pass
        
        # Try different command approaches
        pymol_commands = [
            ['pymol', '-c', '-q', '-e', 'quit'],  # Exit immediately
            ['python', '-c', 'import pymol; print("PyMOL available")'],
            ['python3', '-c', 'import pymol; print("PyMOL available")']
        ]
        
        for cmd in pymol_commands:
            try:
                result = subprocess.run(cmd, 
                                      capture_output=True, 
                                      timeout=10)
                if result.returncode == 0:
                    return True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
                
        # Check if pymol executable exists in common conda locations
        import sys
        python_path = Path(sys.executable)
        
        # Build conda paths dynamically
        conda_pymol_paths = [
            python_path.parent / 'pymol',
            python_path.parent.parent / 'bin' / 'pymol'
        ]
        
        # Add common conda locations across different platforms
        common_conda_roots = [
            Path.home() / 'anaconda3',
            Path.home() / 'miniconda3', 
            Path('/opt/anaconda3'),
            Path('/opt/miniconda3'),
            Path('/usr/local/anaconda3'),
            Path('/usr/local/miniconda3')
        ]
        
        # Add common environment names
        common_env_names = ['bio-mcp', 'biomcp', 'bio_mcp', 'pymol']
        
        for conda_root in common_conda_roots:
            if conda_root.exists():
                # Add base conda pymol
                conda_pymol_paths.append(conda_root / 'bin' / 'pymol')
                
                # Add environment-specific pymol
                for env_name in common_env_names:
                    conda_pymol_paths.append(conda_root / 'envs' / env_name / 'bin' / 'pymol')
        
        for pymol_path in conda_pymol_paths:
            if pymol_path.exists():
                # Test if this pymol works
                try:
                    result = subprocess.run([str(pymol_path), '-c', '-q', '-e', 'quit'], 
                                          capture_output=True, 
                                          timeout=10)
                    if result.returncode == 0:
                        # Store the working pymol path for later use
                        self.pymol_executable = str(pymol_path)
                        return True
                except:
                    continue
        
        return False
    
    async def create_visualization(self, 
                                 pdb_file_path: Path,
                                 style: str = "cartoon",
                                 chains: Optional[List[str]] = None,
                                 residues: Optional[List[str]] = None,
                                 colors: Optional[Dict[str, str]] = None,
                                 output_format: str = "png",
                                 width: int = 800,
                                 height: int = 600) -> Dict[str, Any]:
        """
        Create structure visualization using PyMOL
        
        Args:
            pdb_file_path: Path to PDB file
            style: Visualization style ('cartoon', 'surface', 'sticks', 'spheres', 'ribbon')
            chains: Specific chains to visualize
            residues: Specific residues to highlight
            colors: Color mapping for chains or residues
            output_format: Output format ('png', 'pse', 'wrl')
            width: Image width
            height: Image height
            
        Returns:
            Dict with visualization results
        """
        
        if not self.pymol_available:
            return {
                "success": False,
                "error": "PyMOL is not available. Please ensure PyMOL is installed and accessible."
            }
        
        if not pdb_file_path.exists():
            return {
                "success": False,
                "error": f"PDB file not found: {pdb_file_path}"
            }
        
        # Create unique output filename in organized directory
        base_name = f"visualization_{pdb_file_path.stem}"
        output_file = self.visualization_dir / f"{base_name}.{output_format}"
        script_file = self.temp_dir / f"{base_name}.pml"
        
        try:
            # Generate PyMOL script
            script_content = await self._generate_pymol_script(
                pdb_file_path, output_file, style, chains, residues, colors, width, height
            )
            
            # Write script to file
            with open(script_file, 'w') as f:
                f.write(script_content)
            
            # Run PyMOL
            result = await self._run_pymol_script(script_file)
            
            if not result["success"]:
                return result
            
            # Process output
            if output_format == "png" and output_file.exists():
                # Read image and encode as base64
                with open(output_file, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode()
                
                return {
                    "success": True,
                    "output_type": "image",
                    "format": output_format,
                    "image_data": image_data,
                    "width": width,
                    "height": height,
                    "style": style,
                    "chains": chains,
                    "residues": residues,
                    "file_path": str(output_file)
                }
            elif output_format in ["pse", "wrl"] and output_file.exists():
                return {
                    "success": True,
                    "output_type": "file",
                    "format": output_format,
                    "file_path": str(output_file),
                    "style": style,
                    "chains": chains,
                    "residues": residues
                }
            else:
                return {
                    "success": False,
                    "error": f"Output file not created: {output_file}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            # Clean up script file
            if script_file.exists():
                script_file.unlink()
    
    async def _generate_pymol_script(self, 
                                   pdb_file: Path,
                                   output_file: Path,
                                   style: str,
                                   chains: Optional[List[str]],
                                   residues: Optional[List[str]],
                                   colors: Optional[Dict[str, str]],
                                   width: int,
                                   height: int) -> str:
        """Generate PyMOL script for visualization"""
        
        # Use a safe object name (keep it simple for PyMOL)
        object_name = "mol1"
        
        script_lines = [
            "# PyMOL script generated by BioMCP",
            "reinitialize",
            f"load {pdb_file}, {object_name}",
            "",
            "# Basic setup",
            "hide everything",
            "bg_color white",
            f"viewport {width}, {height}",
            "",
        ]
        
        # Set up selection
        if chains:
            chain_selection = " or ".join([f"chain {c}" for c in chains])
            script_lines.extend([
                f"select target_chains, ({object_name} and ({chain_selection}))",
                f"show {style}, target_chains",
            ])
        else:
            script_lines.append(f"show {style}, {object_name}")
        
        # Color settings
        if colors:
            for target, color in colors.items():
                if chains and target in chains:
                    script_lines.append(f"color {color}, chain {target}")
                elif residues and target in residues:
                    script_lines.append(f"color {color}, resn {target}")
        else:
            # Default coloring
            if style == "cartoon":
                script_lines.append(f"color spectrum, {object_name}")
            elif style == "surface":
                script_lines.append(f"color hydrophobicity, {object_name}")
            else:
                script_lines.append(f"color element, {object_name}")
        
        # Highlight specific residues if specified
        if residues:
            residue_selection = " or ".join([f"resn {r}" for r in residues])
            script_lines.extend([
                f"select highlight_residues, ({object_name} and ({residue_selection}))",
                "show sticks, highlight_residues",
                "color red, highlight_residues",
            ])
        
        # Camera and rendering settings
        script_lines.extend([
            "",
            "# Camera and rendering",
            f"center {object_name}",
            f"zoom {object_name}",
            f"orient {object_name}",
            "ray_trace_mode, 1",
            "set ray_opaque_background, 0" if output_file.suffix == ".png" else "",
            "",
        ])
        
        # Output command
        if output_file.suffix == ".png":
            script_lines.append(f"png {output_file}, ray=1")
        elif output_file.suffix == ".pse":
            script_lines.append(f"save {output_file}")
        elif output_file.suffix == ".wrl":
            script_lines.append(f"save {output_file}")
        
        script_lines.append("quit")
        
        return "\n".join(line for line in script_lines if line is not None)
    
    async def _run_pymol_script(self, script_file: Path) -> Dict[str, Any]:
        """Run PyMOL script"""
        
        if self.use_pymol_module:
            # Use PyMOL as Python module (preferred for conda environments)
            try:
                import pymol
                
                # Initialize PyMOL in headless mode
                pymol.pymol_argv = ['pymol', '-c', '-q']
                pymol.finish_launching()
                
                # Execute the script
                with open(script_file, 'r') as f:
                    script_content = f.read()
                    
                # Execute PyMOL commands
                for line in script_content.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        try:
                            pymol.cmd.do(line)
                        except Exception as cmd_error:
                            print(f"PyMOL command error: {line} -> {cmd_error}")
                
                # Clean up
                pymol.cmd.quit()
                
                return {
                    "success": True,
                    "output": "PyMOL script executed via Python module"
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to run PyMOL via Python module: {str(e)}"
                }
        else:
            # Use PyMOL executable
            cmd = [self.pymol_executable, '-c', '-q', str(script_file)]
            
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(self.temp_dir)
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    return {
                        "success": False,
                        "error": f"PyMOL failed: {stderr.decode()}"
                    }
                
                return {
                    "success": True,
                    "output": stdout.decode()
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to run PyMOL: {str(e)}"
                }
    
    async def analyze_structure(self, pdb_file_path: Path) -> Dict[str, Any]:
        """Analyze structure using PyMOL"""
        
        if not self.pymol_available:
            return {
                "success": False,
                "error": "PyMOL is not available"
            }
        
        if not pdb_file_path.exists():
            return {
                "success": False,
                "error": f"PDB file not found: {pdb_file_path}"
            }
        
        # Create analysis script
        base_name = f"analysis_{pdb_file_path.stem}"
        script_file = self.temp_dir / f"{base_name}.pml"
        output_file = self.visualization_dir / f"{base_name}_analysis.pse"
        
        try:
            # Use a safe object name (keep it simple for PyMOL)
            object_name = "mol1"
            
            script_content = f"""
# PyMOL structure analysis script
reinitialize
load {pdb_file_path}, {object_name}

# Basic information
print "=== STRUCTURE ANALYSIS ==="
print "Atoms:", cmd.count_atoms("{object_name}")
print "Residues:", cmd.count_atoms("{object_name} and name CA")
print "Chains:"
stored.chains = []
cmd.iterate("{object_name} and name CA", "stored.chains.append(chain)")
print set(stored.chains)

# Secondary structure
print "\\n=== SECONDARY STRUCTURE ==="
print "Helices:", cmd.count_atoms("{object_name} and ss H")
print "Sheets:", cmd.count_atoms("{object_name} and ss S")
print "Loops:", cmd.count_atoms("{object_name} and ss L")

# Geometric properties
print "\\n=== GEOMETRIC PROPERTIES ==="
stored.coords = []
cmd.iterate_state(1, "{object_name} and name CA", "stored.coords.append([x,y,z])")
if stored.coords:
    import numpy as np
    coords = np.array(stored.coords)
    center = np.mean(coords, axis=0)
    print "Geometric center:", center
    
    # Calculate radius of gyration
    distances = np.sqrt(np.sum((coords - center)**2, axis=1))
    print "Radius of gyration:", np.sqrt(np.mean(distances**2))
    print "Max distance from center:", np.max(distances)

# Save results
cmd.save("{output_file}")
quit
"""
            
            with open(script_file, 'w') as f:
                f.write(script_content)
            
            # Run analysis
            result = await self._run_pymol_script(script_file)
            
            if not result["success"]:
                return result
            
            # Parse output
            analysis_results = {
                "success": True,
                "structure_file": str(pdb_file_path),
                "analysis_output": result.get("output", ""),
                "session_file": str(output_file) if output_file.exists() else None
            }
            
            return analysis_results
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if script_file.exists():
                script_file.unlink()
    
    async def create_surface_view(self, 
                                pdb_file_path: Path,
                                surface_type: str = "molecular",
                                transparency: float = 0.5,
                                chains: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create surface visualization"""
        
        colors_map = {
            "molecular": "hydrophobicity",
            "electrostatic": "b",
            "hydrophobic": "hydrophobicity"
        }
        
        return await self.create_visualization(
            pdb_file_path=pdb_file_path,
            style="surface",
            chains=chains,
            colors={surface_type: colors_map.get(surface_type, "spectrum")}
        )
    
    async def create_cartoon_view(self, 
                                pdb_file_path: Path,
                                color_scheme: str = "spectrum",
                                chains: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create cartoon visualization"""
        
        return await self.create_visualization(
            pdb_file_path=pdb_file_path,
            style="cartoon",
            chains=chains,
            colors={"cartoon": color_scheme}
        )
    
    async def highlight_residues(self, 
                               pdb_file_path: Path,
                               residue_list: List[str],
                               base_style: str = "cartoon",
                               highlight_style: str = "sticks") -> Dict[str, Any]:
        """Create visualization with highlighted residues"""
        
        return await self.create_visualization(
            pdb_file_path=pdb_file_path,
            style=base_style,
            residues=residue_list
        )
    
    async def launch_gui_session(self, pdb_file_path: Optional[Path] = None) -> Dict[str, Any]:
        """Launch PyMOL GUI with modern pymol_remote control"""
        
        if not self.pymol_available:
            return {
                "success": False,
                "error": "PyMOL is not available"
            }
        
        try:
            # Close existing sessions
            await self._close_gui_session()
            
            if self.pymol_remote_available:
                # Method 1: Try pymol_remote (modern, real-time control)
                result = await self._launch_pymol_remote_session(pdb_file_path)
                if result["success"]:
                    return result
                else:
                    # If pymol_remote fails, inform user but still provide fallback
                    fallback_result = await self._launch_standard_gui_session(pdb_file_path)
                    if fallback_result["success"]:
                        fallback_result["message"] += f"\n\n⚠️ **Note**: pymol_remote failed ({result.get('error', 'unknown error')}). Using script-based control as fallback."
                        fallback_result["pymol_remote_error"] = result.get('error', 'unknown error')
                    return fallback_result
            else:
                # pymol_remote not available, provide fallback with explanation
                fallback_result = await self._launch_standard_gui_session(pdb_file_path)
                if fallback_result["success"]:
                    import_error = self.pymol_remote_import_error or "pymol_remote package not installed"
                    fallback_result["pymol_remote_error"] = f"pymol_remote not available: {import_error}"
                return fallback_result
            
            # Method 2: Fallback to script-based control
            return await self._launch_standard_gui_session(pdb_file_path)
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to launch PyMOL GUI: {str(e)}"
            }
    
    async def _launch_pymol_remote_session(self, pdb_file_path: Optional[Path] = None) -> Dict[str, Any]:
        """Launch PyMOL with pymol_remote for modern real-time control"""
        try:
            # First, start PyMOL with pymol_remote server
            result = await self._start_pymol_remote_server(pdb_file_path)
            if not result["success"]:
                return result
            
            # Wait longer for server to start (PyMOL can be slow to initialize)
            await asyncio.sleep(8)
            
            # Try multiple connection attempts
            connection_attempts = 3
            for attempt in range(connection_attempts):
                connection_result = await self._connect_pymol_remote()
                if connection_result["success"]:
                    return {
                        "success": True,
                        "message": f"PyMOL GUI launched with real-time control (connected on attempt {attempt + 1})",
                        "gui_mode": True,
                        "control_mode": "pymol_remote",
                        "real_time_control": True,
                        "port": self.pymol_remote_port,
                        "loaded_structure": str(pdb_file_path) if pdb_file_path else None
                    }
                else:
                    # Wait between attempts
                    if attempt < connection_attempts - 1:
                        await asyncio.sleep(3)
            
            # All connection attempts failed
            return {
                "success": False,
                "error": f"Failed to connect to pymol_remote server after {connection_attempts} attempts. Last error: {connection_result.get('error', 'unknown')}"
            }
                
        except Exception as e:
            return {"success": False, "error": f"pymol_remote launch failed: {str(e)}"}
    
    async def _start_pymol_remote_server(self, pdb_file_path: Optional[Path] = None) -> Dict[str, Any]:
        """Start PyMOL with pymol_remote server"""
        try:
            # Detect conda environment and create appropriate commands
            conda_env_methods = self._get_conda_pymol_commands(pdb_file_path)
            
            # Try direct path methods first (following PropKa pattern)
            methods = [
                # Method 1: Conda environment direct paths (most likely to work)
                *conda_env_methods,
                
                # Method 2: Generic system commands (fallback, likely to fail in Claude Desktop)
                lambda: ["pymol_remote"] + ([str(pdb_file_path)] if pdb_file_path and pdb_file_path.exists() else []),
                
                # Method 3: PyMOL executable with startup script for remote
                lambda: self._create_pymol_remote_startup_command(pdb_file_path)
            ]
            
            attempted_methods = []
            for i, method in enumerate(methods):
                try:
                    cmd = method()
                    if cmd is None:
                        continue
                    
                    attempted_methods.append(f"Method {i+1}: {' '.join(cmd[:3])}...")
                        
                    # Start the pymol_remote server process
                    self.pymol_gui_process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    # Give the process a moment to start and check if it's still running
                    await asyncio.sleep(1)
                    if self.pymol_gui_process.returncode is not None:
                        # Process died immediately, try to get error output
                        stdout, stderr = await self.pymol_gui_process.communicate()
                        attempted_methods.append(f"Method {i+1} process died: stdout={stdout.decode()[:100]}, stderr={stderr.decode()[:100]}")
                        continue
                    
                    return {"success": True, "message": f"pymol_remote server started (method {i+1}: {' '.join(cmd[:2])})"}
                    
                except FileNotFoundError as e:
                    attempted_methods.append(f"Method {i+1} failed: {str(e)}")
                    if i == len(methods) - 1:  # Last method failed
                        return {"success": False, "error": f"All pymol_remote startup methods failed. Tried: {'; '.join(attempted_methods)}"}
                    continue
                except Exception as e:
                    attempted_methods.append(f"Method {i+1} failed: {str(e)}")
                    if i == len(methods) - 1:  # Last method failed
                        return {"success": False, "error": f"Failed to start pymol_remote server. Tried: {'; '.join(attempted_methods)}"}
                    continue
            
            return {"success": False, "error": "No viable pymol_remote startup method found"}
            
        except Exception as e:
            return {"success": False, "error": f"Failed to start pymol_remote server: {str(e)}"}
    
    def _get_conda_pymol_commands(self, pdb_file_path: Optional[Path] = None) -> List[callable]:
        """Generate pymol_remote commands using the same environment that has working PyMOL"""
        commands = []
        
        # First priority: Use the same environment where PyMOL is working
        if hasattr(self, 'pymol_executable') and self.pymol_executable != 'pymol':
            # Extract the conda environment path from the working pymol executable
            pymol_path = Path(self.pymol_executable)
            if pymol_path.exists():
                # Get the bin directory from the working PyMOL
                bin_dir = pymol_path.parent
                
                # Try pymol_remote in the same directory
                pymol_remote_path = bin_dir / "pymol_remote"
                if pymol_remote_path.exists():
                    same_env_cmd = lambda: [
                        str(pymol_remote_path)
                    ] + ([str(pdb_file_path)] if pdb_file_path and pdb_file_path.exists() else [])
                    commands.append(same_env_cmd)
                
                # Try python in the same directory with pymol_remote module
                python_path = bin_dir / "python"
                if python_path.exists():
                    same_env_python_cmd = lambda: [
                        str(python_path), "-c", 
                        f"""
import pymol
from pymol_remote.server import start_server
import threading
import time

def start_pymol():
    pymol.pymol_argv = ['pymol']
    pymol.finish_launching(['pymol'])
    {'pymol.cmd.load("' + str(pdb_file_path) + '", "structure")' if pdb_file_path and pdb_file_path.exists() else ''}
    {'pymol.cmd.show("cartoon", "structure")' if pdb_file_path and pdb_file_path.exists() else ''}
    start_server(port={self.pymol_remote_port})

if __name__ == '__main__':
    start_pymol()
"""
                    ]
                    commands.append(same_env_python_cmd)
        
        # Second priority: Try other conda environments (fallback)
        common_conda_roots = [
            Path.home() / 'anaconda3',
            Path.home() / 'miniconda3',
            Path('/opt/anaconda3'),
            Path('/opt/miniconda3'),
            Path('/usr/local/anaconda3'),
            Path('/usr/local/miniconda3')
        ]
        
        common_env_names = ['bio_mcp', 'bio-mcp', 'biomcp', 'pymol']
        
        for conda_root in common_conda_roots:
            if conda_root.exists():
                # Environment-specific paths
                for env_name in common_env_names:
                    env_pymol_remote = conda_root / 'envs' / env_name / 'bin' / 'pymol_remote'
                    env_python = conda_root / 'envs' / env_name / 'bin' / 'python'
                    
                    if env_pymol_remote.exists():
                        env_pymol_cmd = lambda env_path=str(env_pymol_remote): [
                            env_path
                        ] + ([str(pdb_file_path)] if pdb_file_path and pdb_file_path.exists() else [])
                        commands.append(env_pymol_cmd)
                    
                    if env_python.exists():
                        env_python_cmd = lambda py_path=str(env_python): [
                            py_path, "-c", 
                            f"""
import pymol
from pymol_remote.server import start_server
import threading
import time

def start_pymol():
    pymol.pymol_argv = ['pymol']
    pymol.finish_launching(['pymol'])
    {'pymol.cmd.load("' + str(pdb_file_path) + '", "structure")' if pdb_file_path and pdb_file_path.exists() else ''}
    {'pymol.cmd.show("cartoon", "structure")' if pdb_file_path and pdb_file_path.exists() else ''}
    start_server(port={self.pymol_remote_port})

if __name__ == '__main__':
    start_pymol()
"""
                        ]
                        commands.append(env_python_cmd)
        
        return commands
    
    def _create_pymol_remote_startup_command(self, pdb_file_path: Optional[Path] = None) -> Optional[List[str]]:
        """Create PyMOL startup command with remote server enabled using direct conda python paths"""
        try:
            # Create a startup script that enables remote server
            startup_script = self.temp_dir / "pymol_remote_startup.py"
            script_content = f"""
import pymol
import sys
import os

# Add pymol_remote to path if needed
try:
    from pymol_remote.server import start_server
    remote_available = True
except ImportError:
    remote_available = False
    print("Warning: pymol_remote not available")

# Initialize PyMOL with GUI
pymol.pymol_argv = ['pymol']
pymol.finish_launching(['pymol'])

# Load structure if provided
{"pymol.cmd.load('" + str(pdb_file_path) + "', 'structure')" if pdb_file_path and pdb_file_path.exists() else ""}
{"pymol.cmd.show('cartoon', 'structure')" if pdb_file_path and pdb_file_path.exists() else ""}
{"pymol.cmd.color('spectrum', 'structure')" if pdb_file_path and pdb_file_path.exists() else ""}

# Start remote server if available
if remote_available:
    try:
        start_server(port={self.pymol_remote_port}, daemon=True)
        print(f"PyMOL remote server started on port {self.pymol_remote_port}")
    except Exception as e:
        print(f"Failed to start remote server: {{e}}")

# Keep PyMOL running
import time
while True:
    time.sleep(1)
"""
            
            with open(startup_script, 'w') as f:
                f.write(script_content)
            
            # Try to find a working python executable, prioritizing the same environment as PyMOL
            python_paths = []
            
            # First priority: Use python from the same environment where PyMOL is working
            if hasattr(self, 'pymol_executable') and self.pymol_executable != 'pymol':
                pymol_path = Path(self.pymol_executable)
                if pymol_path.exists():
                    # Get python from the same bin directory as working PyMOL
                    same_env_python = pymol_path.parent / "python"
                    if same_env_python.exists():
                        python_paths.append(str(same_env_python))
            
            # Second priority: Add other conda environment python paths
            common_conda_roots = [
                Path.home() / 'anaconda3',
                Path.home() / 'miniconda3',
                Path('/opt/anaconda3'),
                Path('/opt/miniconda3'),
                Path('/usr/local/anaconda3'),
                Path('/usr/local/miniconda3')
            ]
            
            common_env_names = ['bio_mcp', 'bio-mcp', 'biomcp', 'pymol']
            
            for conda_root in common_conda_roots:
                if conda_root.exists():
                    # Add environment-specific python
                    for env_name in common_env_names:
                        python_paths.append(str(conda_root / 'envs' / env_name / 'bin' / 'python'))
            
            # Try each python path
            for python_path in python_paths:
                if Path(python_path).exists():
                    return [python_path, str(startup_script)]
            
            # Fallback to generic python (likely to fail in Claude Desktop)
            return ["python", str(startup_script)]
            
        except Exception as e:
            print(f"Failed to create startup script: {e}")
            return None
    
    async def _connect_pymol_remote(self) -> Dict[str, Any]:
        """Connect to the pymol_remote server"""
        try:
            def test_connection():
                try:
                    session = PymolSession(hostname=self.pymol_remote_host, port=self.pymol_remote_port)
                    # Test with a simple command
                    session.do("print 'pymol_remote connected'")
                    return session
                except Exception as e:
                    return None
            
            # Run connection test in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            session = await asyncio.wait_for(
                loop.run_in_executor(None, test_connection),
                timeout=3.0
            )
            
            if session:
                self.pymol_remote_session = session
                return {"success": True, "message": "Connected to pymol_remote server"}
            else:
                return {"success": False, "error": "Failed to connect to pymol_remote server"}
                
        except asyncio.TimeoutError:
            return {"success": False, "error": "Connection to pymol_remote server timed out"}
        except Exception as e:
            return {"success": False, "error": f"pymol_remote connection error: {str(e)}"}
    
    async def _launch_xmlrpc_session(self, pdb_file_path: Optional[Path] = None) -> Dict[str, Any]:
        """Launch PyMOL with XML-RPC server for real-time control"""
        try:
            # Try alternative XML-RPC launch methods
            methods = [
                self._launch_xmlrpc_with_startup_script,
                self._launch_xmlrpc_with_python_module,
                self._launch_xmlrpc_with_command_args
            ]
            
            for method in methods:
                try:
                    result = await method(pdb_file_path)
                    if result["success"]:
                        return result
                except Exception as e:
                    print(f"XML-RPC method failed: {e}")
                    continue
            
            return {"success": False, "error": "All XML-RPC launch methods failed"}
                
        except Exception as e:
            return {"success": False, "error": f"XML-RPC launch failed: {str(e)}"}
    
    async def _launch_xmlrpc_with_startup_script(self, pdb_file_path: Optional[Path] = None) -> Dict[str, Any]:
        """Launch PyMOL with XML-RPC using startup script"""
        # Create startup script that enables XML-RPC
        startup_script = self.temp_dir / "pymol_xmlrpc_startup.pml"
        script_content = f"""# PyMOL XML-RPC startup script
# Enable XML-RPC server
xmlrpc server 127.0.0.1:{self.pymol_rpc_port}

# Load structure if provided
"""
        if pdb_file_path and pdb_file_path.exists():
            script_content += f"load {pdb_file_path}, structure\n"
            script_content += "hide everything\nshow cartoon\ncolor spectrum\ncenter\nzoom\n"
        
        script_content += f"\nprint \"XML-RPC started on port {self.pymol_rpc_port}\"\n"
        
        with open(startup_script, 'w') as f:
            f.write(script_content)
        
        # Launch PyMOL with the startup script
        cmd = [self.pymol_executable, str(startup_script)]
        
        self.pymol_gui_process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Wait for XML-RPC server to start
        await asyncio.sleep(5)
        
        # Test XML-RPC connection
        if await self._test_xmlrpc_connection():
            return {
                "success": True,
                "message": "PyMOL GUI launched with XML-RPC control (startup script)",
                "gui_mode": True,
                "control_mode": "xmlrpc",
                "rpc_port": self.pymol_rpc_port,
                "loaded_structure": str(pdb_file_path) if pdb_file_path else None
            }
        else:
            return {"success": False, "error": "XML-RPC server not responding (startup script)"}
    
    async def _launch_xmlrpc_with_python_module(self, pdb_file_path: Optional[Path] = None) -> Dict[str, Any]:
        """Launch PyMOL with XML-RPC using Python module"""
        if not self.use_pymol_module:
            return {"success": False, "error": "PyMOL module not available"}
        
        try:
            import pymol
            import threading
            
            def pymol_xmlrpc_thread():
                try:
                    # Initialize PyMOL with GUI
                    pymol.pymol_argv = ['pymol']
                    pymol.finish_launching(['pymol'])
                    
                    # Enable XML-RPC server
                    pymol.cmd.do(f"xmlrpc server 127.0.0.1:{self.pymol_rpc_port}")
                    
                    # Load structure if provided
                    if pdb_file_path and pdb_file_path.exists():
                        pymol.cmd.load(str(pdb_file_path), "structure")
                        pymol.cmd.hide("everything")
                        pymol.cmd.show("cartoon")
                        pymol.cmd.color("spectrum")
                        pymol.cmd.center()
                        pymol.cmd.zoom()
                    
                    pass
                    
                except Exception as e:
                    pass
            
            # Start PyMOL in background thread
            gui_thread = threading.Thread(target=pymol_xmlrpc_thread, daemon=True)
            gui_thread.start()
            
            # Give it time to initialize
            await asyncio.sleep(8)
            
            # Test XML-RPC connection
            if await self._test_xmlrpc_connection():
                return {
                    "success": True,
                    "message": "PyMOL GUI launched with XML-RPC control (Python module)",
                    "gui_mode": True,
                    "control_mode": "xmlrpc",
                    "rpc_port": self.pymol_rpc_port,
                    "loaded_structure": str(pdb_file_path) if pdb_file_path else None
                }
            else:
                return {"success": False, "error": "XML-RPC server not responding (Python module)"}
                
        except Exception as e:
            return {"success": False, "error": f"Python module XML-RPC launch failed: {str(e)}"}
    
    async def _launch_xmlrpc_with_command_args(self, pdb_file_path: Optional[Path] = None) -> Dict[str, Any]:
        """Launch PyMOL with XML-RPC using command line arguments"""
        try:
            # Launch PyMOL with XML-RPC enabled via command line
            cmd = [
                self.pymol_executable,
                "-R",  # Enable remote control
                "-x",  # XML-RPC mode
                "-p", str(self.pymol_rpc_port)  # Port
            ]
            
            if pdb_file_path and pdb_file_path.exists():
                cmd.append(str(pdb_file_path))
            
            self.pymol_gui_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for XML-RPC server to start
            await asyncio.sleep(6)
            
            # Test XML-RPC connection
            if await self._test_xmlrpc_connection():
                return {
                    "success": True,
                    "message": "PyMOL GUI launched with XML-RPC control (command args)",
                    "gui_mode": True,
                    "control_mode": "xmlrpc",
                    "rpc_port": self.pymol_rpc_port,
                    "loaded_structure": str(pdb_file_path) if pdb_file_path else None
                }
            else:
                return {"success": False, "error": "XML-RPC server not responding (command args)"}
                
        except Exception as e:
            return {"success": False, "error": f"Command args XML-RPC launch failed: {str(e)}"}
    
    async def _launch_module_gui_session(self, pdb_file_path: Optional[Path] = None) -> Dict[str, Any]:
        """Launch PyMOL using Python module with GUI threading"""
        try:
            import pymol
            import threading
            import time
            
            # Track PyMOL initialization state
            self._pymol_init_complete = False
            self._pymol_init_error = None
            
            def pymol_gui_thread():
                try:
                    # Launch PyMOL with GUI in separate thread
                    pymol.pymol_argv = ['pymol']  # GUI mode
                    pymol.finish_launching(['pymol'])
                    
                    # Mark as launched
                    pymol._pymol_launched = True
                    self._pymol_init_complete = True
                    
                    # Load structure if provided
                    if pdb_file_path and pdb_file_path.exists():
                        pymol.cmd.load(str(pdb_file_path), "structure")
                        pymol.cmd.hide("everything")
                        pymol.cmd.show("cartoon")
                        pymol.cmd.color("spectrum")
                        pymol.cmd.center()
                        pymol.cmd.zoom()
                    
                    # Keep thread alive
                    while True:
                        time.sleep(1)
                        
                except Exception as e:
                    self._pymol_init_error = str(e)
                    self._pymol_init_complete = True  # Mark complete even on error
            
            # Start PyMOL in background thread
            gui_thread = threading.Thread(target=pymol_gui_thread, daemon=True)
            gui_thread.start()
            
            # Wait for initialization with timeout
            timeout = 10
            start_time = time.time()
            while not self._pymol_init_complete and (time.time() - start_time) < timeout:
                await asyncio.sleep(0.5)
            
            if self._pymol_init_error:
                return {"success": False, "error": f"PyMOL initialization failed: {self._pymol_init_error}"}
            
            if not self._pymol_init_complete:
                return {"success": False, "error": "PyMOL initialization timed out"}
            
            return {
                "success": True,
                "message": "PyMOL GUI launched via Python module with real-time control",
                "gui_mode": True,
                "control_mode": "module",
                "real_time_control": True,
                "loaded_structure": str(pdb_file_path) if pdb_file_path else None
            }
            
        except Exception as e:
            return {"success": False, "error": f"Module GUI launch failed: {str(e)}"}
    
    async def _launch_standard_gui_session(self, pdb_file_path: Optional[Path] = None) -> Dict[str, Any]:
        """Launch standard PyMOL GUI with script-based control"""
        try:
            # Create a simple startup script if structure is provided
            if pdb_file_path and pdb_file_path.exists():
                startup_script = self.temp_dir / "pymol_startup.pml"
                script_content = f"""# PyMOL Startup Script
load {pdb_file_path}, structure
hide everything
show cartoon
color spectrum
center
zoom
"""
                with open(startup_script, 'w') as f:
                    f.write(script_content)
                
                cmd = [self.pymol_executable, str(startup_script)]
            else:
                cmd = [self.pymol_executable]
            
            self.pymol_gui_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await asyncio.sleep(3)
            
            return {
                "success": True,
                "message": "PyMOL GUI launched with script-based control",
                "gui_mode": True,
                "control_mode": "script",
                "loaded_structure": str(pdb_file_path) if pdb_file_path else None
            }
            
        except Exception as e:
            return {"success": False, "error": f"Standard GUI launch failed: {str(e)}"}
    
    async def _test_xmlrpc_connection(self) -> bool:
        """Test if XML-RPC server is responding"""
        try:
            # Test connection asynchronously with multiple attempts
            def test_connection():
                try:
                    client = xmlrpc.client.ServerProxy(f"http://127.0.0.1:{self.pymol_rpc_port}", allow_none=True)
                    
                    # Try multiple simple commands to test responsiveness
                    test_commands = [
                        "print 'XML-RPC test'",
                        "cmd.get_version()",
                        "cmd.count_atoms('all')"
                    ]
                    
                    for cmd in test_commands:
                        try:
                            result = client.do(cmd)
                            return True
                        except Exception as e:
                            continue
                    
                    return False
                except Exception as e:
                    return False
            
            # Run in thread pool since xmlrpc is blocking, with timeout
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, test_connection),
                timeout=5.0
            )
            return result
            
        except asyncio.TimeoutError:
            return False
        except Exception as e:
            return False
    
    async def execute_pymol_command(self, command: str) -> Dict[str, Any]:
        """Execute a PyMOL command with modern pymol_remote control"""
        
        try:
            # Method 1: Try to connect to existing pymol_remote session if not connected
            if not self.pymol_remote_session and self.pymol_remote_available:
                connection_result = await self._connect_pymol_remote()
                # Don't return error if connection fails, just continue to other methods
            
            # Method 2: Try pymol_remote for real-time execution (best option)
            if self.pymol_remote_session:
                result = await self._execute_via_pymol_remote(command)
                if result["success"]:
                    return result
            
            # Method 3: Check if GUI process is active for script fallback
            gui_status = await self.get_gui_status()
            if gui_status.get("gui_active"):
                return await self._execute_via_script(command)
            
            # Method 4: No PyMOL session available
            return {
                "success": False,
                "error": "No PyMOL session available. Please either:\n1. Run 'pymol_remote' in terminal for real-time control, or\n2. Use 'launch_pymol_gui' tool for script-based control"
            }
                
        except Exception as e:
            return {
                "success": False,
                "command": command,
                "error": f"Failed to execute command: {str(e)}"
            }
    
    async def _execute_via_pymol_remote(self, command: str) -> Dict[str, Any]:
        """Execute command via pymol_remote (modern real-time execution)"""
        try:
            if not self.pymol_remote_session:
                return {"success": False, "error": "No pymol_remote session available"}
            
            def execute_command():
                try:
                    # Execute command using pymol_remote
                    result = self.pymol_remote_session.do(command)
                    return {"success": True, "output": str(result) if result else "Command executed successfully"}
                except Exception as e:
                    return {"success": False, "error": str(e)}
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, execute_command)
            
            if result["success"]:
                return {
                    "success": True,
                    "command": command,
                    "output": result["output"],
                    "execution_method": "pymol_remote",
                    "message": f"✅ Command executed in real-time: {command}"
                }
            else:
                return {"success": False, "error": f"pymol_remote execution failed: {result['error']}"}
                
        except Exception as e:
            return {"success": False, "error": f"pymol_remote execution error: {str(e)}"}
    
    async def _execute_via_xmlrpc(self, command: str) -> Dict[str, Any]:
        """Execute command via XML-RPC (real-time)"""
        try:
            def execute_command():
                try:
                    client = xmlrpc.client.ServerProxy(f"http://127.0.0.1:{self.pymol_rpc_port}")
                    result = client.do(command)
                    return {"success": True, "output": result}
                except Exception as e:
                    return {"success": False, "error": str(e)}
            
            # Run in thread pool since xmlrpc is blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, execute_command)
            
            if result["success"]:
                return {
                    "success": True,
                    "command": command,
                    "output": result.get("output", ""),
                    "execution_method": "xmlrpc",
                    "message": f"Command executed in real-time: {command}"
                }
            else:
                return {"success": False, "error": f"XML-RPC execution failed: {result['error']}"}
                
        except Exception as e:
            return {"success": False, "error": f"XML-RPC not available: {str(e)}"}
    
    async def _execute_via_module(self, command: str) -> Dict[str, Any]:
        """Execute command via PyMOL Python module"""
        try:
            if self.use_pymol_module:
                import pymol
                
                def execute_command():
                    try:
                        # Check if PyMOL is already launched
                        if not hasattr(pymol, '_pymol_launched'):
                            return {"success": False, "error": "PyMOL not initialized"}
                        
                        # Execute command and capture any output
                        if command.strip():
                            # Handle different command types
                            if command.startswith('print '):
                                # Handle print commands specially
                                eval_cmd = command[6:].strip()
                                try:
                                    result = eval(eval_cmd)
                                    return {"success": True, "output": str(result)}
                                except:
                                    pymol.cmd.do(command)
                                    return {"success": True, "output": "Print command executed"}
                            else:
                                # Standard PyMOL command
                                result = pymol.cmd.do(command)
                                if result is not None:
                                    return {"success": True, "output": str(result)}
                                else:
                                    return {"success": True, "output": "Command executed successfully"}
                        else:
                            return {"success": False, "error": "Empty command"}
                    except Exception as e:
                        return {"success": False, "error": str(e)}
                
                # Run in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, execute_command)
                
                if result["success"]:
                    return {
                        "success": True,
                        "command": command,
                        "output": result["output"],
                        "execution_method": "module",
                        "message": f"✅ Command executed in real-time: {command}"
                    }
                else:
                    return {"success": False, "error": f"Module execution failed: {result['error']}"}
            else:
                return {"success": False, "error": "PyMOL module not available"}
                
        except Exception as e:
            return {"success": False, "error": f"Module execution error: {str(e)}"}
    
    async def _execute_via_script(self, command: str) -> Dict[str, Any]:
        """Fallback: Execute command via script file"""
        try:
            timestamp = int(time.time() * 1000)
            script_file = self.visualization_dir / f"realtime_command_{timestamp}.pml"
            
            # Create a more informative script
            script_content = f"""# PyMOL Command Script - Generated by Bio MCP
# Command: {command}
# Created: {timestamp}

# Execute the command
{command}

# Confirmation message
print "✅ Executed: {command}"
print "📝 Script: {script_file.name}"
"""
            
            with open(script_file, 'w') as f:
                f.write(script_content)
            
            return {
                "success": True,
                "command": command,
                "output": f"Command script created at: {script_file}",
                "execution_method": "script",
                "script_file": str(script_file),
                "manual_execution_needed": True,
                "instructions": f"In PyMOL GUI, run: @{script_file}",
                "alternative_instructions": f"Or copy-paste in PyMOL: {command}",
                "message": f"📝 **PyMOL Command Script Created**\n\n• Command: `{command}`\n• Execution: Script-based\n• Status: Script ready\n\n**Instructions:**\nIn PyMOL GUI, execute: `@{script_file}`\nScript saved to: {script_file}\n\n**Output:**\nCommand script created at: {script_file}"
            }
                
        except Exception as e:
            return {
                "success": False,
                "command": command,
                "error": f"Script creation failed: {str(e)}"
            }
    
    async def load_structure_in_gui(self, pdb_file_path: Path, object_name: str = "structure") -> Dict[str, Any]:
        """Load a structure in the active PyMOL GUI session with real-time execution"""
        
        if not pdb_file_path.exists():
            return {
                "success": False,
                "error": f"PDB file not found: {pdb_file_path}"
            }
        
        # Try to execute commands in real-time
        commands = [
            f"load {pdb_file_path}, {object_name}",
            f"hide everything, {object_name}",
            f"show cartoon, {object_name}", 
            f"color spectrum, {object_name}",
            f"center {object_name}",
            f"zoom {object_name}"
        ]
        
        results = []
        execution_method = None
        
        for command in commands:
            result = await self.execute_pymol_command(command)
            results.append(result)
            if result["success"] and not execution_method:
                execution_method = result.get("execution_method", "unknown")
        
        successful_commands = sum(1 for r in results if r["success"])
        
        if successful_commands > 0:
            return {
                "success": True,
                "loaded_structure": str(pdb_file_path),
                "object_name": object_name,
                "execution_method": execution_method,
                "commands_executed": successful_commands,
                "total_commands": len(commands),
                "results": results,
                "message": f"Structure loaded with {execution_method} execution ({successful_commands}/{len(commands)} commands succeeded)"
            }
        else:
            # Fallback to script creation
            return await self._create_load_structure_script(pdb_file_path, object_name)
    
    async def _create_load_structure_script(self, pdb_file_path: Path, object_name: str) -> Dict[str, Any]:
        """Fallback: Create script for loading structure"""
        timestamp = int(time.time() * 1000)
        script_file = self.visualization_dir / f"load_structure_{object_name}_{timestamp}.pml"
        
        script_content = f"""# Load and visualize structure: {object_name}
# Generated by Bio MCP

# Load the structure
load {pdb_file_path}, {object_name}

# Basic visualization setup
hide everything, {object_name}
show cartoon, {object_name}
color spectrum, {object_name}

# Center and zoom on the structure
center {object_name}
zoom {object_name}

# Optional: Set nice rendering
set ray_opaque_background, 0
set ray_trace_mode, 1

print "Structure {object_name} loaded and visualized successfully"
"""
        
        try:
            with open(script_file, 'w') as f:
                f.write(script_content)
            
            return {
                "success": True,
                "loaded_structure": str(pdb_file_path),
                "object_name": object_name,
                "execution_method": "script",
                "script_file": str(script_file),
                "instructions": f"In PyMOL GUI, run: @{script_file}",
                "manual_commands": [
                    f"load {pdb_file_path}, {object_name}",
                    f"hide everything, {object_name}",
                    f"show cartoon, {object_name}",
                    f"color spectrum, {object_name}",
                    f"center {object_name}",
                    f"zoom {object_name}"
                ],
                "message": f"Structure loading script created. Load it in PyMOL GUI with: @{script_file}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create loading script: {str(e)}"
            }
    
    async def apply_visualization_style(self, object_name: str, style: str, color: str = "spectrum") -> Dict[str, Any]:
        """Apply visualization style in GUI session"""
        
        style_commands = {
            "cartoon": [
                f"hide everything, {object_name}",
                f"show cartoon, {object_name}",
                f"color {color}, {object_name}"
            ],
            "surface": [
                f"hide everything, {object_name}",
                f"show surface, {object_name}",
                f"color {color}, {object_name}"
            ],
            "sticks": [
                f"hide everything, {object_name}",
                f"show sticks, {object_name}",
                f"color {color}, {object_name}"
            ],
            "spheres": [
                f"hide everything, {object_name}",
                f"show spheres, {object_name}",
                f"color {color}, {object_name}"
            ]
        }
        
        commands = style_commands.get(style, style_commands["cartoon"])
        
        # Create script file
        import time
        timestamp = int(time.time() * 1000)
        script_file = self.visualization_dir / f"apply_style_{style}_{timestamp}.pml"
        
        script_content = f"""# Apply {style} style to {object_name}
# Generated by Bio MCP

# Apply visualization style
"""
        for command in commands:
            script_content += f"{command}\n"
        
        script_content += f"""
# Center and refresh view
center {object_name}
zoom {object_name}

print "Applied {style} style with {color} coloring to {object_name}"
"""
        
        try:
            with open(script_file, 'w') as f:
                f.write(script_content)
            
            return {
                "success": True,
                "style": style,
                "color": color,
                "object_name": object_name,
                "script_file": str(script_file),
                "instructions": f"In PyMOL GUI, run: @{script_file}",
                "manual_commands": commands,
                "message": f"Style script created. Apply {style} style in PyMOL GUI with: @{script_file}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create style script: {str(e)}"
            }
    
    async def highlight_residues_in_gui(self, object_name: str, residue_selections: List[str], color: str = "red") -> Dict[str, Any]:
        """Highlight specific residues in GUI session"""
        
        # Create script file
        import time
        timestamp = int(time.time() * 1000)
        script_file = self.visualization_dir / f"highlight_residues_{timestamp}.pml"
        
        script_content = f"""# Highlight residues in {object_name}
# Generated by Bio MCP

# Create selections and highlight residues
"""
        
        commands = []
        for i, selection in enumerate(residue_selections):
            selection_name = f"highlight_{i}"
            commands.extend([
                f"select {selection_name}, {object_name} and ({selection})",
                f"show sticks, {selection_name}",
                f"color {color}, {selection_name}"
            ])
        
        for command in commands:
            script_content += f"{command}\n"
        
        script_content += f"""
# Refresh view
center {object_name}
zoom {object_name}

print "Highlighted {len(residue_selections)} residue selection(s) in {color}"
"""
        
        try:
            with open(script_file, 'w') as f:
                f.write(script_content)
            
            return {
                "success": True,
                "highlighted_selections": residue_selections,
                "color": color,
                "object_name": object_name,
                "script_file": str(script_file),
                "instructions": f"In PyMOL GUI, run: @{script_file}",
                "manual_commands": commands,
                "message": f"Highlighting script created. Highlight residues in PyMOL GUI with: @{script_file}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create highlighting script: {str(e)}"
            }
    
    async def _close_gui_session(self) -> Dict[str, Any]:
        """Close the PyMOL GUI session and cleanup pymol_remote connection"""
        
        # Close pymol_remote session
        if self.pymol_remote_session:
            try:
                # Try to close gracefully
                def close_session():
                    try:
                        self.pymol_remote_session.do("quit")
                    except:
                        pass
                
                loop = asyncio.get_event_loop()
                await asyncio.wait_for(
                    loop.run_in_executor(None, close_session),
                    timeout=2.0
                )
            except:
                pass
            finally:
                self.pymol_remote_session = None
        
        # Close process
        if self.pymol_gui_process and self.pymol_gui_process.returncode is None:
            try:
                self.pymol_gui_process.terminate()
                await asyncio.wait_for(self.pymol_gui_process.wait(), timeout=5.0)
                return {"success": True, "message": "PyMOL GUI session closed"}
            except asyncio.TimeoutError:
                self.pymol_gui_process.kill()
                return {"success": True, "message": "PyMOL GUI session forcefully closed"}
            except Exception as e:
                return {"success": False, "error": f"Failed to close GUI session: {str(e)}"}
        
        return {"success": True, "message": "No active GUI session to close"}
    
    async def get_gui_status(self) -> Dict[str, Any]:
        """Get status of PyMOL GUI session with pymol_remote support"""
        
        gui_active = self.pymol_gui_process and self.pymol_gui_process.returncode is None
        pymol_remote_connected = self.pymol_remote_session is not None
        
        # Determine control method
        if pymol_remote_connected:
            control_method = "pymol_remote (real-time)"
        elif gui_active:
            control_method = "script (manual)"
        else:
            control_method = "none"
        
        return {
            "gui_active": gui_active,
            "process_id": self.pymol_gui_process.pid if gui_active else None,
            "pymol_available": self.pymol_available,
            "control_method": control_method,
            
            # Modern pymol_remote status
            "pymol_remote_available": self.pymol_remote_available,
            "pymol_remote_connected": pymol_remote_connected,
            "pymol_remote_port": self.pymol_remote_port if pymol_remote_connected else None,
            
            # Legacy methods (disabled)
            "xmlrpc_available": False,
            "xmlrpc_port": None,
            "module_available": False,
            
            "script_fallback": True,
            "pymol_executable": self.pymol_executable,
            "real_time_execution": pymol_remote_connected
        }
    
    # Modern pymol_remote convenience methods
    
    async def load_structure_pymol_remote(self, file_path: Path, object_name: str = "structure") -> Dict[str, Any]:
        """Load structure using pymol_remote with real-time feedback"""
        if not self.pymol_remote_session:
            return {"success": False, "error": "No pymol_remote session available"}
        
        try:
            def load_structure():
                try:
                    # Load the structure
                    result = self.pymol_remote_session.load(str(file_path), object_name)
                    
                    # Apply nice visualization
                    self.pymol_remote_session.do(f"hide everything, {object_name}")
                    self.pymol_remote_session.do(f"show cartoon, {object_name}")
                    self.pymol_remote_session.do(f"color spectrum, {object_name}")
                    self.pymol_remote_session.do(f"center {object_name}")
                    self.pymol_remote_session.do(f"zoom {object_name}")
                    
                    return {"success": True, "result": str(result)}
                except Exception as e:
                    return {"success": False, "error": str(e)}
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, load_structure)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"✅ Structure loaded with real-time visualization: {object_name}",
                    "file_path": str(file_path),
                    "object_name": object_name,
                    "execution_method": "pymol_remote"
                }
            else:
                return result
                
        except Exception as e:
            return {"success": False, "error": f"Failed to load structure: {str(e)}"}
    
    async def fetch_structure_pymol_remote(self, pdb_id: str) -> Dict[str, Any]:
        """Fetch structure from PDB using pymol_remote"""
        if not self.pymol_remote_session:
            return {"success": False, "error": "No pymol_remote session available"}
        
        try:
            def fetch_structure():
                try:
                    result = self.pymol_remote_session.fetch(pdb_id)
                    
                    # Apply nice visualization
                    self.pymol_remote_session.do(f"hide everything, {pdb_id}")
                    self.pymol_remote_session.do(f"show cartoon, {pdb_id}")
                    self.pymol_remote_session.do(f"color spectrum, {pdb_id}")
                    self.pymol_remote_session.do(f"center {pdb_id}")
                    self.pymol_remote_session.do(f"zoom {pdb_id}")
                    
                    return {"success": True, "result": str(result)}
                except Exception as e:
                    return {"success": False, "error": str(e)}
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, fetch_structure)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"✅ Structure fetched with real-time visualization: {pdb_id}",
                    "pdb_id": pdb_id,
                    "execution_method": "pymol_remote"
                }
            else:
                return result
                
        except Exception as e:
            return {"success": False, "error": f"Failed to fetch structure: {str(e)}"}
    
    async def apply_style_pymol_remote(self, style: str, selection: str = "all") -> Dict[str, Any]:
        """Apply visualization style using pymol_remote"""
        if not self.pymol_remote_session:
            return {"success": False, "error": "No pymol_remote session available"}
        
        try:
            def apply_style():
                try:
                    self.pymol_remote_session.do(f"hide everything, {selection}")
                    self.pymol_remote_session.do(f"show {style}, {selection}")
                    return {"success": True}
                except Exception as e:
                    return {"success": False, "error": str(e)}
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, apply_style)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"✅ Style applied in real-time: {style} to {selection}",
                    "style": style,
                    "selection": selection,
                    "execution_method": "pymol_remote"
                }
            else:
                return result
                
        except Exception as e:
            return {"success": False, "error": f"Failed to apply style: {str(e)}"}
    
    async def color_selection_pymol_remote(self, color: str, selection: str = "all") -> Dict[str, Any]:
        """Color selection using pymol_remote"""
        if not self.pymol_remote_session:
            return {"success": False, "error": "No pymol_remote session available"}
        
        try:
            def apply_color():
                try:
                    self.pymol_remote_session.do(f"color {color}, {selection}")
                    return {"success": True}
                except Exception as e:
                    return {"success": False, "error": str(e)}
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, apply_color)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"✅ Color applied in real-time: {color} to {selection}",
                    "color": color,
                    "selection": selection,
                    "execution_method": "pymol_remote"
                }
            else:
                return result
                
        except Exception as e:
            return {"success": False, "error": f"Failed to apply color: {str(e)}"}