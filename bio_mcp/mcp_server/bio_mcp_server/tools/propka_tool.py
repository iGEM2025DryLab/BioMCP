import os
import tempfile
import subprocess
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
import json

class PropkaTool:
    """PROPKA integration for pKa calculations"""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "bio_mcp_propka"
        self.temp_dir.mkdir(exist_ok=True)
        self.propka_available = self._check_propka_available()
    
    def _check_propka_available(self) -> bool:
        """Check if PROPKA is available"""
        # Build propka paths dynamically
        propka_paths = ['propka3']
        
        # Add common conda locations
        common_conda_roots = [
            Path.home() / 'anaconda3',
            Path.home() / 'miniconda3',
            Path('/opt/anaconda3'),
            Path('/opt/miniconda3'), 
            Path('/usr/local/anaconda3'),
            Path('/usr/local/miniconda3')
        ]
        
        common_env_names = ['bio-mcp', 'biomcp', 'bio_mcp', 'propka']
        
        for conda_root in common_conda_roots:
            if conda_root.exists():
                # Add base conda propka3
                propka_paths.append(str(conda_root / 'bin' / 'propka3'))
                
                # Add environment-specific propka3
                for env_name in common_env_names:
                    propka_paths.append(str(conda_root / 'envs' / env_name / 'bin' / 'propka3'))
        
        # Check for direct executable
        for propka_path in propka_paths:
            try:
                if Path(propka_path).exists() or propka_path == 'propka3':
                    result = subprocess.run([propka_path, '--help'], 
                                          capture_output=True, 
                                          timeout=5)
                    if result.returncode == 0:
                        return True
            except:
                continue
        
        # Check for Python module
        python_paths = ['python3', 'python']
        
        # Add conda python paths
        for conda_root in common_conda_roots:
            if conda_root.exists():
                python_paths.append(str(conda_root / 'bin' / 'python'))
                for env_name in common_env_names:
                    python_paths.append(str(conda_root / 'envs' / env_name / 'bin' / 'python'))
        
        for python_path in python_paths:
            try:
                result = subprocess.run([python_path, '-c', 'import propka; print("PROPKA available")'], 
                                      capture_output=True, 
                                      timeout=5)
                if result.returncode == 0:
                    return True
            except:
                continue
                
        return False
    
    async def calculate_pka(self, 
                          pdb_file_path: Path, 
                          ph: float = 7.0,
                          chains: Optional[List[str]] = None,
                          residue_range: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """
        Calculate pKa values using PROPKA
        
        Args:
            pdb_file_path: Path to PDB file
            ph: pH value for calculation
            chains: Specific chains to analyze
            residue_range: Dict with 'start' and 'end' residue numbers
            
        Returns:
            Dict with pKa results and analysis
        """
        
        if not self.propka_available:
            return {
                "success": False,
                "error": "PROPKA is not available. Please ensure propka3 is installed and accessible."
            }
        
        if not pdb_file_path.exists():
            raise FileNotFoundError(f"PDB file not found: {pdb_file_path}")
        
        # Create temporary file for PROPKA input
        temp_pdb = self.temp_dir / f"temp_{pdb_file_path.stem}.pdb"
        
        # Prepare PDB file content (filter chains/residues if specified)
        await self._prepare_pdb_file(pdb_file_path, temp_pdb, chains, residue_range)
        
        try:
            # Run PROPKA
            result = await self._run_propka(temp_pdb, ph)
            
            # Parse results
            parsed_results = await self._parse_propka_output(temp_pdb, result)
            
            return {
                "success": True,
                "ph": ph,
                "input_file": str(pdb_file_path),
                "chains_analyzed": chains or "all",
                "residue_range": residue_range,
                "results": parsed_results,
                "summary": await self._generate_summary(parsed_results, ph)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "ph": ph,
                "input_file": str(pdb_file_path)
            }
        finally:
            # Clean up temporary files
            if temp_pdb.exists():
                temp_pdb.unlink()
            
            # Clean up PROPKA output files
            for ext in ['.pka', '.propka']:
                output_file = temp_pdb.with_suffix(ext)
                if output_file.exists():
                    output_file.unlink()
    
    async def _prepare_pdb_file(self, 
                               source_pdb: Path, 
                               target_pdb: Path,
                               chains: Optional[List[str]] = None,
                               residue_range: Optional[Dict[str, int]] = None):
        """Prepare PDB file with optional filtering"""
        
        with open(source_pdb, 'r') as src, open(target_pdb, 'w') as dst:
            for line in src:
                if line.startswith(('ATOM', 'HETATM')):
                    chain_id = line[21]
                    residue_num = int(line[22:26].strip())
                    
                    # Filter by chain if specified
                    if chains and chain_id not in chains:
                        continue
                    
                    # Filter by residue range if specified
                    if residue_range:
                        if residue_num < residue_range.get('start', 0) or \
                           residue_num > residue_range.get('end', 99999):
                            continue
                    
                    dst.write(line)
                elif line.startswith(('HEADER', 'TITLE', 'COMPND', 'SOURCE', 'REMARK')):
                    dst.write(line)
                elif line.startswith('END'):
                    dst.write(line)
                    break
    
    async def _run_propka(self, pdb_file: Path, ph: float) -> str:
        """Run PROPKA calculation"""
        
        # Try different PROPKA execution methods dynamically
        propka_commands = [['propka3', str(pdb_file)]]
        
        # Add conda-specific commands
        common_conda_roots = [
            Path.home() / 'anaconda3',
            Path.home() / 'miniconda3',
            Path('/opt/anaconda3'),
            Path('/opt/miniconda3'),
            Path('/usr/local/anaconda3'),
            Path('/usr/local/miniconda3')
        ]
        
        common_env_names = ['bio-mcp', 'biomcp', 'bio_mcp', 'propka']
        
        for conda_root in common_conda_roots:
            if conda_root.exists():
                # Add base conda propka3
                propka_commands.append([str(conda_root / 'bin' / 'propka3'), str(pdb_file)])
                propka_commands.append([str(conda_root / 'bin' / 'python'), '-m', 'propka3.propka', str(pdb_file)])
                
                # Add environment-specific commands
                for env_name in common_env_names:
                    env_propka = conda_root / 'envs' / env_name / 'bin' / 'propka3'
                    env_python = conda_root / 'envs' / env_name / 'bin' / 'python'
                    if env_propka.exists():
                        propka_commands.append([str(env_propka), str(pdb_file)])
                    if env_python.exists():
                        propka_commands.append([str(env_python), '-m', 'propka3.propka', str(pdb_file)])
        
        # Add generic python approaches
        propka_commands.extend([
            ['python3', '-m', 'propka3.propka', str(pdb_file)],
            ['python', '-m', 'propka3.propka', str(pdb_file)]
        ])
        
        last_error = None
        
        for cmd in propka_commands:
            try:
                # Run PROPKA asynchronously
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(self.temp_dir)
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    return stdout.decode()
                else:
                    last_error = f"PROPKA failed with {' '.join(cmd)}: {stderr.decode()}"
                    
            except FileNotFoundError as e:
                last_error = f"Command not found: {' '.join(cmd)}"
                continue
            except Exception as e:
                last_error = f"Error with {' '.join(cmd)}: {str(e)}"
                continue
        
        raise RuntimeError(f"PROPKA not found. Please ensure propka3 is installed. Last error: {last_error}")
    
    async def _parse_propka_output(self, pdb_file: Path, propka_output: str) -> Dict[str, Any]:
        """Parse PROPKA output files"""
        
        results = {
            "ionizable_groups": [],
            "pka_values": {},
            "buried_groups": [],
            "surface_groups": []
        }
        
        # Try to read .pka file first (main source of data)
        pka_file = pdb_file.with_suffix('.pka')
        if pka_file.exists():
            pka_results = await self._parse_pka_file(pka_file)
            results.update(pka_results)
            
            # Extract ionizable groups from pka file
            if "detailed_analysis" in pka_results:
                for item in pka_results["detailed_analysis"]:
                    if isinstance(item, dict) and "residue" in item and "pka" in item:
                        # Parse residue info: "ASP  19 A" -> residue="ASP", residue_number="19", chain="A"
                        residue_parts = item["residue"].split()
                        if len(residue_parts) >= 3:
                            residue_type = residue_parts[0]
                            residue_number = residue_parts[1]
                            chain = residue_parts[2]
                            
                            group_info = {
                                "residue": residue_type,
                                "chain": chain,
                                "pka": item["pka"],
                                "residue_number": residue_number
                            }
                            
                            results["ionizable_groups"].append(group_info)
                            
                            # Group by residue type
                            if residue_type not in results["pka_values"]:
                                results["pka_values"][residue_type] = []
                            results["pka_values"][residue_type].append(item["pka"])
        
        return results
    
    async def _parse_pka_file(self, pka_file: Path) -> Dict[str, Any]:
        """Parse detailed .pka file"""
        
        results = {
            "detailed_analysis": [],
            "interactions": [],
            "desolvation_effects": []
        }
        
        try:
            with open(pka_file, 'r') as f:
                content = f.read()
                
            # Parse the PROPKA output format
            lines = content.split('\n')
            parsing_data = False
            
            for line in lines:
                line = line.strip()
                
                # Look for the data section (after the header)
                if line.startswith('---------  -----   ------'):
                    parsing_data = True
                    continue
                    
                if not parsing_data or not line:
                    continue
                    
                # Parse residue data lines
                # Format: "ASP  19 A   5.48   100 %    4.48  630   0.79    0   -0.85 THR 100 A   -0.79 ILE  99 A   -0.44 LYS 102 A"
                if line and not line.startswith('-') and not line.startswith('RESIDUE'):
                    parts = line.split()
                    if len(parts) >= 4:
                        try:
                            residue_type = parts[0]
                            residue_number = parts[1]
                            chain = parts[2]
                            pka_value = float(parts[3])
                            
                            residue_key = f"{residue_type}  {residue_number} {chain}"
                            
                            # Check if we already have this residue
                            existing_residue = None
                            for res in results["detailed_analysis"]:
                                if res["residue"] == residue_key:
                                    existing_residue = res
                                    break
                            
                            if not existing_residue:
                                residue_info = {
                                    "residue": residue_key,
                                    "pka": pka_value,
                                    "interactions": []
                                }
                                results["detailed_analysis"].append(residue_info)
                            else:
                                # Additional interaction line for same residue
                                if len(parts) > 4:
                                    interaction_info = " ".join(parts[4:])
                                    existing_residue["interactions"].append(interaction_info)
                                    
                        except (ValueError, IndexError):
                            # This might be a continuation line with interactions
                            if results["detailed_analysis"]:
                                interaction_info = line
                                results["detailed_analysis"][-1]["interactions"].append(interaction_info)
                            continue
                        
        except Exception as e:
            results["parse_error"] = str(e)
        
        return results
    
    async def _generate_summary(self, results: Dict[str, Any], ph: float) -> Dict[str, Any]:
        """Generate human-readable summary of pKa results"""
        
        summary = {
            "total_ionizable_groups": len(results.get("ionizable_groups", [])),
            "unique_residue_types": len(results.get("pka_values", {})),
            "ph_used": ph,
            "significant_shifts": [],
            "statistics": {}
        }
        
        # Standard pKa values for comparison
        standard_pka = {
            "ASP": 3.9,
            "GLU": 4.3,
            "HIS": 6.0,
            "CYS": 8.3,
            "TYR": 10.1,
            "LYS": 10.5,
            "ARG": 12.5
        }
        
        # Calculate statistics and significant shifts
        for residue_type, pka_values in results.get("pka_values", {}).items():
            if residue_type in standard_pka:
                avg_pka = sum(pka_values) / len(pka_values)
                standard = standard_pka[residue_type]
                shift = avg_pka - standard
                
                summary["statistics"][residue_type] = {
                    "count": len(pka_values),
                    "average_pka": round(avg_pka, 2),
                    "standard_pka": standard,
                    "average_shift": round(shift, 2),
                    "range": [round(min(pka_values), 2), round(max(pka_values), 2)]
                }
                
                # Identify significant shifts (>1.0 pKa units)
                if abs(shift) > 1.0:
                    summary["significant_shifts"].append({
                        "residue": residue_type,
                        "shift": round(shift, 2),
                        "direction": "higher" if shift > 0 else "lower"
                    })
        
        # Calculate protonation states at given pH
        summary["protonation_states"] = {}
        for group in results.get("ionizable_groups", []):
            residue = group["residue"]
            pka = group["pka"]
            
            # Calculate fraction protonated
            if residue in ["ASP", "GLU", "CYS", "TYR"]:  # Acidic groups
                fraction_protonated = 1 / (1 + 10**(ph - pka))
            else:  # Basic groups
                fraction_protonated = 1 / (1 + 10**(pka - ph))
            
            if residue not in summary["protonation_states"]:
                summary["protonation_states"][residue] = []
            
            summary["protonation_states"][residue].append({
                "chain": group["chain"],
                "residue_number": group.get("residue_number"),
                "pka": pka,
                "fraction_protonated": round(fraction_protonated, 3)
            })
        
        return summary
    
    async def get_ionizable_residues(self, pdb_file_path: Path) -> List[Dict[str, Any]]:
        """Get list of ionizable residues in structure without running PROPKA"""
        
        ionizable_residues = []
        ionizable_types = {"ASP", "GLU", "HIS", "CYS", "TYR", "LYS", "ARG"}
        
        if not pdb_file_path.exists():
            return ionizable_residues
        
        seen_residues = set()
        
        with open(pdb_file_path, 'r') as f:
            for line in f:
                if line.startswith('ATOM'):
                    residue_name = line[17:20].strip()
                    chain_id = line[21]
                    residue_number = line[22:26].strip()
                    
                    if residue_name in ionizable_types:
                        residue_key = f"{chain_id}:{residue_number}:{residue_name}"
                        if residue_key not in seen_residues:
                            seen_residues.add(residue_key)
                            ionizable_residues.append({
                                "residue": residue_name,
                                "chain": chain_id,
                                "residue_number": residue_number,
                                "standard_pka": {
                                    "ASP": 3.9, "GLU": 4.3, "HIS": 6.0, "CYS": 8.3,
                                    "TYR": 10.1, "LYS": 10.5, "ARG": 12.5
                                }.get(residue_name, None)
                            })
        
        return ionizable_residues