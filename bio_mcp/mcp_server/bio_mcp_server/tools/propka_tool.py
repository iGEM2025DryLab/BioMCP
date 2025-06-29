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
        
        cmd = [
            'python', '-m', 'propka3.propka',
            '--ph', str(ph),
            '--quiet',
            str(pdb_file)
        ]
        
        try:
            # Run PROPKA asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.temp_dir)
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"PROPKA failed: {stderr.decode()}")
            
            return stdout.decode()
            
        except FileNotFoundError:
            raise RuntimeError("PROPKA not found. Please ensure propka3 is installed.")
    
    async def _parse_propka_output(self, pdb_file: Path, propka_output: str) -> Dict[str, Any]:
        """Parse PROPKA output files"""
        
        results = {
            "ionizable_groups": [],
            "pka_values": {},
            "buried_groups": [],
            "surface_groups": []
        }
        
        # Try to read .pka file first
        pka_file = pdb_file.with_suffix('.pka')
        if pka_file.exists():
            results.update(await self._parse_pka_file(pka_file))
        
        # Parse stdout output
        lines = propka_output.split('\n')
        in_summary = False
        
        for line in lines:
            line = line.strip()
            
            if 'SUMMARY' in line:
                in_summary = True
                continue
            
            if in_summary and line and not line.startswith('-'):
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        residue = parts[0]
                        chain = parts[1] if len(parts) > 1 else 'A'
                        pka_value = float(parts[2])
                        
                        group_info = {
                            "residue": residue,
                            "chain": chain,
                            "pka": pka_value,
                            "residue_number": parts[3] if len(parts) > 3 else None
                        }
                        
                        results["ionizable_groups"].append(group_info)
                        
                        # Group by residue type
                        if residue not in results["pka_values"]:
                            results["pka_values"][residue] = []
                        results["pka_values"][residue].append(pka_value)
                        
                    except (ValueError, IndexError):
                        continue
        
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
                
            # Parse detailed information
            lines = content.split('\n')
            current_residue = None
            
            for line in lines:
                line = line.strip()
                
                if line.startswith('pKa'):
                    # Parse pKa line
                    parts = line.split()
                    if len(parts) >= 3:
                        residue_info = {
                            "residue": parts[1],
                            "pka": float(parts[2]),
                            "interactions": []
                        }
                        results["detailed_analysis"].append(residue_info)
                        current_residue = residue_info
                
                elif line and current_residue and ('HIS' in line or 'ASP' in line or 'GLU' in line or 'LYS' in line or 'TYR' in line):
                    # Parse interaction line
                    if 'Side chain' in line or 'Backbone' in line:
                        current_residue["interactions"].append(line)
                        
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