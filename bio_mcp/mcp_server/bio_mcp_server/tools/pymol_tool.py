import os
import tempfile
import subprocess
import asyncio
import base64
from pathlib import Path
from typing import Dict, List, Optional, Any
import json

class PyMOLTool:
    """PyMOL integration for structure visualization"""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "bio_mcp_pymol"
        self.temp_dir.mkdir(exist_ok=True)
        self.pymol_available = self._check_pymol_available()
    
    def _check_pymol_available(self) -> bool:
        """Check if PyMOL is available"""
        try:
            result = subprocess.run(['pymol', '-c', '-q'], 
                                  capture_output=True, 
                                  timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
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
        
        # Create unique output filename
        base_name = f"visualization_{pdb_file_path.stem}"
        output_file = self.temp_dir / f"{base_name}.{output_format}"
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
        
        script_lines = [
            "# PyMOL script generated by BioMCP",
            "reinitialize",
            f"load {pdb_file}, structure",
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
                f"select target_chains, {chain_selection}",
                f"show {style}, target_chains",
            ])
        else:
            script_lines.append(f"show {style}, structure")
        
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
                script_lines.append("color spectrum, structure")
            elif style == "surface":
                script_lines.append("color hydrophobicity, structure")
            else:
                script_lines.append("color element, structure")
        
        # Highlight specific residues if specified
        if residues:
            residue_selection = " or ".join([f"resn {r}" for r in residues])
            script_lines.extend([
                f"select highlight_residues, {residue_selection}",
                "show sticks, highlight_residues",
                "color red, highlight_residues",
            ])
        
        # Camera and rendering settings
        script_lines.extend([
            "",
            "# Camera and rendering",
            "center structure",
            "zoom structure",
            "orient structure",
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
        
        cmd = ['pymol', '-c', '-q', str(script_file)]
        
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
        output_file = self.temp_dir / f"{base_name}_analysis.txt"
        
        try:
            script_content = f"""
# PyMOL structure analysis script
reinitialize
load {pdb_file_path}, structure

# Basic information
print "=== STRUCTURE ANALYSIS ==="
print "Atoms:", cmd.count_atoms("structure")
print "Residues:", cmd.count_atoms("structure and name CA")
print "Chains:"
stored.chains = []
cmd.iterate("structure and name CA", "stored.chains.append(chain)")
print set(stored.chains)

# Secondary structure
print "\\n=== SECONDARY STRUCTURE ==="
print "Helices:", cmd.count_atoms("structure and ss H")
print "Sheets:", cmd.count_atoms("structure and ss S")
print "Loops:", cmd.count_atoms("structure and ss L")

# Geometric properties
print "\\n=== GEOMETRIC PROPERTIES ==="
stored.coords = []
cmd.iterate_state(1, "structure and name CA", "stored.coords.append([x,y,z])")
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
cmd.save("{output_file.with_suffix('.pse')}")
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
                "session_file": str(output_file.with_suffix('.pse')) if output_file.with_suffix('.pse').exists() else None
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