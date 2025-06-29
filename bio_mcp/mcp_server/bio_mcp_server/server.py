import asyncio
import json
import base64
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel

from bio_mcp_server.file_system import BioFileSystem
from bio_mcp_server.tools.propka_tool import PropkaTool
from bio_mcp_server.tools.pymol_tool import PyMOLTool

class BioMCPServer:
    """MCP Server for biological research tools"""
    
    def __init__(self):
        self.server = Server("bio-mcp-server")
        self.file_system = BioFileSystem()
        self.propka_tool = PropkaTool()
        self.pymol_tool = PyMOLTool()
        self._register_tools()
    
    def _register_tools(self):
        """Register all available tools"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="upload_file",
                    description="Upload a file to the bio file system. Content should be base64 encoded.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string", "description": "Name of the file"},
                            "content": {"type": "string", "description": "Base64 encoded file content"}
                        },
                        "required": ["filename", "content"]
                    }
                ),
                Tool(
                    name="list_files",
                    description="List all files in the bio file system with optional filtering",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "bio_type": {
                                "type": "string", 
                                "enum": ["structure", "dna", "rna", "protein", "small_molecule"],
                                "description": "Filter by biological file type"
                            }
                        }
                    }
                ),
                Tool(
                    name="get_file_info",
                    description="Get detailed information about a specific file",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_id": {"type": "string", "description": "ID of the file"}
                        },
                        "required": ["file_id"]
                    }
                ),
                Tool(
                    name="read_file_content",
                    description="Read file content with optional line range to manage context",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_id": {"type": "string", "description": "ID of the file"},
                            "start_line": {"type": "integer", "default": 0, "description": "Starting line number (0-based)"},
                            "max_lines": {"type": "integer", "default": 1000, "description": "Maximum number of lines to read"}
                        },
                        "required": ["file_id"]
                    }
                ),
                Tool(
                    name="search_file_content",
                    description="Search for patterns in file content",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_id": {"type": "string", "description": "ID of the file"},
                            "pattern": {"type": "string", "description": "Regular expression pattern to search for"},
                            "max_matches": {"type": "integer", "default": 100, "description": "Maximum number of matches to return"}
                        },
                        "required": ["file_id", "pattern"]
                    }
                ),
                Tool(
                    name="read_pdb_header",
                    description="Extract and read only the header information from a PDB file",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_id": {"type": "string", "description": "ID of the PDB file"}
                        },
                        "required": ["file_id"]
                    }
                ),
                Tool(
                    name="get_sequence_range",
                    description="Get a specific range of sequences from a FASTA file",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_id": {"type": "string", "description": "ID of the sequence file"},
                            "sequence_index": {"type": "integer", "description": "Index of the sequence (0-based)"},
                            "start_pos": {"type": "integer", "default": 0, "description": "Starting position in sequence"},
                            "length": {"type": "integer", "default": 100, "description": "Length of sequence to extract"}
                        },
                        "required": ["file_id", "sequence_index"]
                    }
                ),
                Tool(
                    name="select_pdb_chains",
                    description="Extract specific chains from a PDB structure",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_id": {"type": "string", "description": "ID of the PDB file"},
                            "chains": {"type": "array", "items": {"type": "string"}, "description": "List of chain IDs to extract"}
                        },
                        "required": ["file_id", "chains"]
                    }
                ),
                Tool(
                    name="find_residues",
                    description="Find specific residues in a structure file",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_id": {"type": "string", "description": "ID of the structure file"},
                            "residue_names": {"type": "array", "items": {"type": "string"}, "description": "List of residue names to find"},
                            "chain": {"type": "string", "description": "Specific chain to search in (optional)"}
                        },
                        "required": ["file_id", "residue_names"]
                    }
                ),
                Tool(
                    name="calculate_pka",
                    description="Calculate pKa values for ionizable residues using PROPKA",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_id": {"type": "string", "description": "ID of the PDB structure file"},
                            "ph": {"type": "number", "default": 7.0, "description": "pH value for calculation"},
                            "chains": {"type": "array", "items": {"type": "string"}, "description": "Specific chains to analyze (optional)"},
                            "residue_range": {
                                "type": "object",
                                "properties": {
                                    "start": {"type": "integer", "description": "Starting residue number"},
                                    "end": {"type": "integer", "description": "Ending residue number"}
                                },
                                "description": "Residue range to analyze (optional)"
                            }
                        },
                        "required": ["file_id"]
                    }
                ),
                Tool(
                    name="list_ionizable_residues",
                    description="List all ionizable residues in a structure without running PROPKA",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_id": {"type": "string", "description": "ID of the PDB structure file"}
                        },
                        "required": ["file_id"]
                    }
                ),
                Tool(
                    name="visualize_structure",
                    description="Create structure visualization using PyMOL",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_id": {"type": "string", "description": "ID of the PDB structure file"},
                            "style": {
                                "type": "string",
                                "enum": ["cartoon", "surface", "sticks", "spheres", "ribbon"],
                                "default": "cartoon",
                                "description": "Visualization style"
                            },
                            "chains": {"type": "array", "items": {"type": "string"}, "description": "Specific chains to visualize"},
                            "residues": {"type": "array", "items": {"type": "string"}, "description": "Specific residues to highlight"},
                            "width": {"type": "integer", "default": 800, "description": "Image width"},
                            "height": {"type": "integer", "default": 600, "description": "Image height"}
                        },
                        "required": ["file_id"]
                    }
                ),
                Tool(
                    name="create_surface_view",
                    description="Create molecular surface visualization",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_id": {"type": "string", "description": "ID of the PDB structure file"},
                            "surface_type": {
                                "type": "string",
                                "enum": ["molecular", "electrostatic", "hydrophobic"],
                                "default": "molecular",
                                "description": "Type of surface to display"
                            },
                            "chains": {"type": "array", "items": {"type": "string"}, "description": "Specific chains to visualize"}
                        },
                        "required": ["file_id"]
                    }
                ),
                Tool(
                    name="analyze_structure_pymol",
                    description="Analyze protein structure using PyMOL (secondary structure, geometry, etc.)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_id": {"type": "string", "description": "ID of the PDB structure file"}
                        },
                        "required": ["file_id"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            try:
                if name == "upload_file":
                    return await self._upload_file(arguments)
                elif name == "list_files":
                    return await self._list_files(arguments)
                elif name == "get_file_info":
                    return await self._get_file_info(arguments)
                elif name == "read_file_content":
                    return await self._read_file_content(arguments)
                elif name == "search_file_content":
                    return await self._search_file_content(arguments)
                elif name == "read_pdb_header":
                    return await self._read_pdb_header(arguments)
                elif name == "get_sequence_range":
                    return await self._get_sequence_range(arguments)
                elif name == "select_pdb_chains":
                    return await self._select_pdb_chains(arguments)
                elif name == "find_residues":
                    return await self._find_residues(arguments)
                elif name == "calculate_pka":
                    return await self._calculate_pka(arguments)
                elif name == "list_ionizable_residues":
                    return await self._list_ionizable_residues(arguments)
                elif name == "visualize_structure":
                    return await self._visualize_structure(arguments)
                elif name == "create_surface_view":
                    return await self._create_surface_view(arguments)
                elif name == "analyze_structure_pymol":
                    return await self._analyze_structure_pymol(arguments)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error executing tool {name}: {str(e)}")]
    
    async def _upload_file(self, args: Dict[str, Any]) -> List[TextContent]:
        """Upload file to file system"""
        filename = args["filename"]
        content_b64 = args["content"]
        
        try:
            content = base64.b64decode(content_b64)
            file_id = await self.file_system.upload_file(filename, content)
            
            return [TextContent(
                type="text",
                text=f"File uploaded successfully. File ID: {file_id}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Failed to upload file: {str(e)}"
            )]
    
    async def _list_files(self, args: Dict[str, Any]) -> List[TextContent]:
        """List files in the file system"""
        bio_type = args.get("bio_type")
        files = await self.file_system.list_files(bio_type)
        
        if not files:
            return [TextContent(
                type="text",
                text="No files found" + (f" of type '{bio_type}'" if bio_type else "")
            )]
        
        result = f"Found {len(files)} file(s)" + (f" of type '{bio_type}'" if bio_type else "") + ":\n\n"
        
        for file_info in files:
            result += f"• **{file_info['filename']}** (ID: {file_info['file_id']})\n"
            result += f"  Type: {file_info['bio_type'] or 'Unknown'} | Size: {file_info['size']:,} bytes\n"
            result += f"  Summary: {file_info['summary']}\n"
            result += f"  Uploaded: {file_info['upload_time']}\n\n"
        
        return [TextContent(type="text", text=result)]
    
    async def _get_file_info(self, args: Dict[str, Any]) -> List[TextContent]:
        """Get detailed file information"""
        file_id = args["file_id"]
        info = await self.file_system.get_file_info(file_id)
        
        if not info:
            return [TextContent(
                type="text",
                text=f"File with ID '{file_id}' not found"
            )]
        
        result = f"**File Information: {info['filename']}**\n\n"
        result += f"• File ID: {info['file_id']}\n"
        result += f"• Type: {info['bio_type'] or 'Unknown'}\n"
        result += f"• Size: {info['size']:,} bytes\n"
        result += f"• File Format: {info['file_type']}\n"
        result += f"• Uploaded: {info['upload_time']}\n"
        result += f"• Checksum: {info['checksum']}\n"
        result += f"• Summary: {info['summary']}\n"
        
        if info['additional_info']:
            result += "\n**Additional Information:**\n"
            for key, value in info['additional_info'].items():
                if isinstance(value, list):
                    result += f"• {key.title()}: {', '.join(map(str, value))}\n"
                else:
                    result += f"• {key.title()}: {value}\n"
        
        return [TextContent(type="text", text=result)]
    
    async def _read_file_content(self, args: Dict[str, Any]) -> List[TextContent]:
        """Read file content with line range"""
        file_id = args["file_id"]
        start_line = args.get("start_line", 0)
        max_lines = args.get("max_lines", 1000)
        
        content = await self.file_system.read_file_content(file_id, start_line, max_lines)
        
        if content is None:
            return [TextContent(
                type="text",
                text=f"File with ID '{file_id}' not found"
            )]
        
        result = f"**File Content** (lines {start_line + 1}-{start_line + max_lines}):\n\n"
        result += f"```\n{content}\n```"
        
        return [TextContent(type="text", text=result)]
    
    async def _search_file_content(self, args: Dict[str, Any]) -> List[TextContent]:
        """Search file content for patterns"""
        file_id = args["file_id"]
        pattern = args["pattern"]
        max_matches = args.get("max_matches", 100)
        
        matches = await self.file_system.search_file_content(file_id, pattern, max_matches)
        
        if matches is None:
            return [TextContent(
                type="text",
                text=f"File with ID '{file_id}' not found"
            )]
        
        if not matches:
            return [TextContent(
                type="text",
                text=f"No matches found for pattern '{pattern}'"
            )]
        
        result = f"**Search Results** for pattern '{pattern}' ({len(matches)} matches):\n\n"
        
        for match in matches:
            result += f"• Line {match['line_number']}: {match['content']}\n"
            if match['match']:
                result += f"  Match: `{match['match']}`\n"
        
        return [TextContent(type="text", text=result)]
    
    async def _read_pdb_header(self, args: Dict[str, Any]) -> List[TextContent]:
        """Read only PDB header information"""
        file_id = args["file_id"]
        
        # Read first 100 lines which typically contain header info
        content = await self.file_system.read_file_content(file_id, 0, 100)
        
        if content is None:
            return [TextContent(
                type="text",
                text=f"File with ID '{file_id}' not found"
            )]
        
        # Extract header lines
        header_lines = []
        for line in content.split('\n'):
            if line.startswith(('HEADER', 'TITLE', 'COMPND', 'SOURCE', 'KEYWDS', 
                               'EXPDTA', 'AUTHOR', 'REVDAT', 'REMARK')):
                header_lines.append(line)
            elif line.startswith('ATOM'):
                break  # Stop at first ATOM record
        
        if not header_lines:
            return [TextContent(
                type="text",
                text="No header information found in PDB file"
            )]
        
        result = "**PDB Header Information:**\n\n"
        result += "```\n" + '\n'.join(header_lines) + "\n```"
        
        return [TextContent(type="text", text=result)]
    
    async def _get_sequence_range(self, args: Dict[str, Any]) -> List[TextContent]:
        """Get sequence range from FASTA file"""
        file_id = args["file_id"]
        sequence_index = args["sequence_index"]
        start_pos = args.get("start_pos", 0)
        length = args.get("length", 100)
        
        content = await self.file_system.read_file_content(file_id)
        
        if content is None:
            return [TextContent(
                type="text",
                text=f"File with ID '{file_id}' not found"
            )]
        
        # Parse FASTA content
        sequences = content.split('>')
        if len(sequences) <= sequence_index + 1:
            return [TextContent(
                type="text",
                text=f"Sequence index {sequence_index} not found in file"
            )]
        
        seq_data = sequences[sequence_index + 1].strip().split('\n')
        header = seq_data[0]
        sequence = ''.join(seq_data[1:])
        
        # Extract requested range
        end_pos = min(start_pos + length, len(sequence))
        sequence_range = sequence[start_pos:end_pos]
        
        result = f"**Sequence Range** (positions {start_pos + 1}-{end_pos}):\n\n"
        result += f"Header: {header}\n"
        result += f"Length: {len(sequence_range)} residues\n\n"
        result += f"```\n{sequence_range}\n```"
        
        return [TextContent(type="text", text=result)]
    
    async def _select_pdb_chains(self, args: Dict[str, Any]) -> List[TextContent]:
        """Select specific chains from PDB file"""
        file_id = args["file_id"]
        chains = args["chains"]
        
        content = await self.file_system.read_file_content(file_id)
        
        if content is None:
            return [TextContent(
                type="text",
                text=f"File with ID '{file_id}' not found"
            )]
        
        # Filter lines for specified chains
        filtered_lines = []
        for line in content.split('\n'):
            if line.startswith(('ATOM', 'HETATM')):
                if line[21] in chains:
                    filtered_lines.append(line)
            elif line.startswith(('HEADER', 'TITLE', 'COMPND', 'SOURCE', 'REMARK')):
                filtered_lines.append(line)
        
        if not any(line.startswith(('ATOM', 'HETATM')) for line in filtered_lines):
            return [TextContent(
                type="text",
                text=f"No atoms found for chains: {', '.join(chains)}"
            )]
        
        result = f"**Selected Chains** ({', '.join(chains)}):\n\n"
        result += f"```\n" + '\n'.join(filtered_lines) + "\n```"
        
        return [TextContent(type="text", text=result)]
    
    async def _find_residues(self, args: Dict[str, Any]) -> List[TextContent]:
        """Find specific residues in structure file"""
        file_id = args["file_id"]
        residue_names = args["residue_names"]
        chain = args.get("chain")
        
        content = await self.file_system.read_file_content(file_id)
        
        if content is None:
            return [TextContent(
                type="text",
                text=f"File with ID '{file_id}' not found"
            )]
        
        # Find matching residues
        found_residues = []
        for line in content.split('\n'):
            if line.startswith(('ATOM', 'HETATM')):
                residue_name = line[17:20].strip()
                line_chain = line[21]
                
                if residue_name in residue_names:
                    if chain is None or line_chain == chain:
                        found_residues.append({
                            'residue': residue_name,
                            'chain': line_chain,
                            'residue_number': line[22:26].strip(),
                            'line': line
                        })
        
        if not found_residues:
            chain_text = f" in chain {chain}" if chain else ""
            return [TextContent(
                type="text",
                text=f"No residues found for: {', '.join(residue_names)}{chain_text}"
            )]
        
        result = f"**Found Residues** ({len(found_residues)} matches):\n\n"
        
        current_residue = None
        for res in found_residues:
            res_key = f"{res['chain']}:{res['residue_number']}:{res['residue']}"
            if current_residue != res_key:
                current_residue = res_key
                result += f"• {res['residue']} (Chain {res['chain']}, Residue {res['residue_number']})\n"
        
        return [TextContent(type="text", text=result)]
    
    async def _calculate_pka(self, args: Dict[str, Any]) -> List[TextContent]:
        """Calculate pKa values using PROPKA"""
        file_id = args["file_id"]
        ph = args.get("ph", 7.0)
        chains = args.get("chains")
        residue_range = args.get("residue_range")
        
        # Get file path
        file_path = await self.file_system.get_file_path(file_id)
        if file_path is None:
            return [TextContent(
                type="text",
                text=f"File with ID '{file_id}' not found"
            )]
        
        # Check if it's a structure file
        file_info = await self.file_system.get_file_info(file_id)
        if file_info and file_info.get("bio_type") != "structure":
            return [TextContent(
                type="text",
                text=f"File '{file_id}' is not a structure file. PROPKA requires PDB files."
            )]
        
        # Run PROPKA calculation
        try:
            result = await self.propka_tool.calculate_pka(
                file_path, ph, chains, residue_range
            )
            
            if not result["success"]:
                return [TextContent(
                    type="text",
                    text=f"PROPKA calculation failed: {result.get('error', 'Unknown error')}"
                )]
            
            # Format results
            output = f"**PROPKA pKa Calculation Results**\n\n"
            output += f"• File: {result['input_file']}\n"
            output += f"• pH: {result['ph']}\n"
            output += f"• Chains analyzed: {result['chains_analyzed']}\n"
            
            if result.get('residue_range'):
                output += f"• Residue range: {result['residue_range']['start']}-{result['residue_range']['end']}\n"
            
            # Summary statistics
            summary = result.get("summary", {})
            output += f"\n**Summary:**\n"
            output += f"• Total ionizable groups: {summary.get('total_ionizable_groups', 0)}\n"
            output += f"• Unique residue types: {summary.get('unique_residue_types', 0)}\n"
            
            # Significant shifts
            significant_shifts = summary.get("significant_shifts", [])
            if significant_shifts:
                output += f"\n**Significant pKa Shifts (>1.0 units):**\n"
                for shift in significant_shifts:
                    output += f"• {shift['residue']}: {shift['shift']:+.2f} ({shift['direction']} than standard)\n"
            
            # Statistics by residue type
            stats = summary.get("statistics", {})
            if stats:
                output += f"\n**Statistics by Residue Type:**\n"
                for residue, stat in stats.items():
                    output += f"• **{residue}** ({stat['count']} residues):\n"
                    output += f"  - Average pKa: {stat['average_pka']} (standard: {stat['standard_pka']})\n"
                    output += f"  - Average shift: {stat['average_shift']:+.2f}\n"
                    output += f"  - Range: {stat['range'][0]} - {stat['range'][1]}\n"
            
            # Individual results
            ionizable_groups = result.get("results", {}).get("ionizable_groups", [])
            if ionizable_groups:
                output += f"\n**Individual pKa Values:**\n"
                for group in ionizable_groups[:20]:  # Limit to first 20 for context
                    output += f"• {group['residue']} {group['chain']}:{group.get('residue_number', '?')} - pKa: {group['pka']:.2f}\n"
                
                if len(ionizable_groups) > 20:
                    output += f"... and {len(ionizable_groups) - 20} more residues\n"
            
            return [TextContent(type="text", text=output)]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error running PROPKA calculation: {str(e)}"
            )]
    
    async def _list_ionizable_residues(self, args: Dict[str, Any]) -> List[TextContent]:
        """List ionizable residues in structure"""
        file_id = args["file_id"]
        
        # Get file path
        file_path = await self.file_system.get_file_path(file_id)
        if file_path is None:
            return [TextContent(
                type="text",
                text=f"File with ID '{file_id}' not found"
            )]
        
        # Check if it's a structure file
        file_info = await self.file_system.get_file_info(file_id)
        if file_info and file_info.get("bio_type") != "structure":
            return [TextContent(
                type="text",
                text=f"File '{file_id}' is not a structure file."
            )]
        
        try:
            residues = await self.propka_tool.get_ionizable_residues(file_path)
            
            if not residues:
                return [TextContent(
                    type="text",
                    text="No ionizable residues found in structure"
                )]
            
            # Group by residue type
            by_type = {}
            for residue in residues:
                res_type = residue["residue"]
                if res_type not in by_type:
                    by_type[res_type] = []
                by_type[res_type].append(residue)
            
            output = f"**Ionizable Residues Found** ({len(residues)} total):\n\n"
            
            for res_type, res_list in sorted(by_type.items()):
                standard_pka = res_list[0]["standard_pka"]
                output += f"**{res_type}** ({len(res_list)} residues, standard pKa: {standard_pka}):\n"
                
                for residue in res_list:
                    output += f"• Chain {residue['chain']}, Residue {residue['residue_number']}\n"
                output += "\n"
            
            output += "Use `calculate_pka` to determine actual pKa values for these residues."
            
            return [TextContent(type="text", text=output)]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error listing ionizable residues: {str(e)}"
            )]
    
    async def _visualize_structure(self, args: Dict[str, Any]) -> List[TextContent]:
        """Create structure visualization using PyMOL"""
        file_id = args["file_id"]
        style = args.get("style", "cartoon")
        chains = args.get("chains")
        residues = args.get("residues")
        width = args.get("width", 800)
        height = args.get("height", 600)
        
        # Get file path
        file_path = await self.file_system.get_file_path(file_id)
        if file_path is None:
            return [TextContent(
                type="text",
                text=f"File with ID '{file_id}' not found"
            )]
        
        # Check if it's a structure file
        file_info = await self.file_system.get_file_info(file_id)
        if file_info and file_info.get("bio_type") != "structure":
            return [TextContent(
                type="text",
                text=f"File '{file_id}' is not a structure file. PyMOL requires PDB files."
            )]
        
        try:
            result = await self.pymol_tool.create_visualization(
                pdb_file_path=file_path,
                style=style,
                chains=chains,
                residues=residues,
                width=width,
                height=height
            )
            
            if not result["success"]:
                return [TextContent(
                    type="text",
                    text=f"Visualization failed: {result.get('error', 'Unknown error')}"
                )]
            
            if result["output_type"] == "image":
                # For now, just return info about the image since MCP doesn't handle images directly
                output = f"**Structure Visualization Created**\n\n"
                output += f"• Style: {result['style']}\n"
                output += f"• Dimensions: {result['width']}x{result['height']}\n"
                output += f"• Format: {result['format']}\n"
                
                if result.get('chains'):
                    output += f"• Chains: {', '.join(result['chains'])}\n"
                if result.get('residues'):
                    output += f"• Highlighted residues: {', '.join(result['residues'])}\n"
                
                output += f"• Image saved to: {result['file_path']}\n"
                output += f"• Image data available (base64 encoded, {len(result['image_data'])} characters)\n"
                
                return [TextContent(type="text", text=output)]
            else:
                output = f"**Structure File Created**\n\n"
                output += f"• Format: {result['format']}\n"
                output += f"• File path: {result['file_path']}\n"
                
                return [TextContent(type="text", text=output)]
                
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error creating visualization: {str(e)}"
            )]
    
    async def _create_surface_view(self, args: Dict[str, Any]) -> List[TextContent]:
        """Create surface visualization"""
        file_id = args["file_id"]
        surface_type = args.get("surface_type", "molecular")
        chains = args.get("chains")
        
        # Get file path
        file_path = await self.file_system.get_file_path(file_id)
        if file_path is None:
            return [TextContent(
                type="text",
                text=f"File with ID '{file_id}' not found"
            )]
        
        # Check if it's a structure file
        file_info = await self.file_system.get_file_info(file_id)
        if file_info and file_info.get("bio_type") != "structure":
            return [TextContent(
                type="text",
                text=f"File '{file_id}' is not a structure file."
            )]
        
        try:
            result = await self.pymol_tool.create_surface_view(
                pdb_file_path=file_path,
                surface_type=surface_type,
                chains=chains
            )
            
            if not result["success"]:
                return [TextContent(
                    type="text",
                    text=f"Surface visualization failed: {result.get('error', 'Unknown error')}"
                )]
            
            output = f"**Surface Visualization Created**\n\n"
            output += f"• Surface type: {surface_type}\n"
            output += f"• Style: {result['style']}\n"
            
            if result.get('chains'):
                output += f"• Chains: {', '.join(result['chains'])}\n"
            
            if result["output_type"] == "image":
                output += f"• Image dimensions: {result['width']}x{result['height']}\n"
                output += f"• Image saved to: {result['file_path']}\n"
            
            return [TextContent(type="text", text=output)]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error creating surface view: {str(e)}"
            )]
    
    async def _analyze_structure_pymol(self, args: Dict[str, Any]) -> List[TextContent]:
        """Analyze structure using PyMOL"""
        file_id = args["file_id"]
        
        # Get file path
        file_path = await self.file_system.get_file_path(file_id)
        if file_path is None:
            return [TextContent(
                type="text",
                text=f"File with ID '{file_id}' not found"
            )]
        
        # Check if it's a structure file
        file_info = await self.file_system.get_file_info(file_id)
        if file_info and file_info.get("bio_type") != "structure":
            return [TextContent(
                type="text",
                text=f"File '{file_id}' is not a structure file."
            )]
        
        try:
            result = await self.pymol_tool.analyze_structure(file_path)
            
            if not result["success"]:
                return [TextContent(
                    type="text",
                    text=f"Structure analysis failed: {result.get('error', 'Unknown error')}"
                )]
            
            output = f"**PyMOL Structure Analysis**\n\n"
            output += f"• Input file: {result['structure_file']}\n"
            
            if result.get("session_file"):
                output += f"• PyMOL session saved: {result['session_file']}\n"
            
            # Parse analysis output
            analysis_output = result.get("analysis_output", "")
            if analysis_output:
                output += f"\n**Analysis Results:**\n"
                output += f"```\n{analysis_output}\n```"
            else:
                output += "\nAnalysis completed successfully."
            
            return [TextContent(type="text", text=output)]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error analyzing structure: {str(e)}"
            )]
    
    async def run(self, transport_type: str = "stdio"):
        """Run the MCP server"""
        if transport_type == "stdio":
            from mcp.server.stdio import stdio_server
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(read_stream, write_stream, 
                                    self.server.create_initialization_options())
        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")