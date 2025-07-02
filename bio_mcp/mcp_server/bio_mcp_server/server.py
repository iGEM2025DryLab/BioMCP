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
                    description="📁 Upload biological files (PDB, FASTA, etc.) to the research workspace. Files are automatically categorized by type and made available for analysis.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string", "description": "File name with extension (e.g., 'protein.pdb', 'sequence.fasta')"},
                            "content": {"type": "string", "description": "Base64 encoded file content - use btoa() in JavaScript or base64.b64encode() in Python"}
                        },
                        "required": ["filename", "content"]
                    }
                ),
                Tool(
                    name="list_files",
                    description="📋 Browse all uploaded biological files with intelligent filtering. View structures, sequences, and analysis results organized by type.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "bio_type": {
                                "type": "string", 
                                "enum": ["structure", "dna", "rna", "protein", "small_molecule"],
                                "description": "Filter by biological data type: 'structure' for PDB/mmCIF, 'protein' for sequences, 'dna'/'rna' for nucleic acids"
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
                    description="📖 Smart file content reader with context management. Efficiently handles large biological files (PDB, FASTA) by reading specific sections. Automatically formats content for analysis.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_id": {"type": "string", "description": "ID of uploaded file to read"},
                            "start_line": {"type": "integer", "default": 0, "description": "Starting line number (0-based). For PDB files: 0=header, ~10=structure data"},
                            "max_lines": {"type": "integer", "default": 1000, "description": "Maximum lines to read (prevents context overflow). For large files, read in chunks."}
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
                    description="📄 Extract PDB header metadata including protein name, resolution, experimental method, publication info, and structural annotations. Essential for understanding structure context.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_id": {"type": "string", "description": "ID of uploaded PDB structure file"}
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
                    description="🧪 Advanced pKa analysis using PROPKA3 - Calculate ionization states of ASP, GLU, HIS, CYS, TYR, LYS, ARG residues. Predicts protonation at different pH values with detailed interaction analysis.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_id": {"type": "string", "description": "ID of uploaded PDB structure file to analyze"},
                            "ph": {"type": "number", "default": 7.0, "description": "pH value for protonation state calculation (typical range: 1-14, physiological ~7.4)"},
                            "chains": {"type": "array", "items": {"type": "string"}, "description": "Specific protein chains to analyze (e.g., ['A', 'B']). Leave empty for all chains."},
                            "residue_range": {
                                "type": "object",
                                "properties": {
                                    "start": {"type": "integer", "description": "Starting residue number (inclusive)"},
                                    "end": {"type": "integer", "description": "Ending residue number (inclusive)"}
                                },
                                "description": "Optional residue number range to focus analysis on specific protein regions"
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
                    description="🎨 Generate publication-quality protein structure images using PyMOL. Creates static visualizations with customizable styles, colors, and highlighting for presentations and analysis.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_id": {"type": "string", "description": "ID of uploaded PDB structure file to visualize"},
                            "style": {
                                "type": "string",
                                "enum": ["cartoon", "surface", "sticks", "spheres", "ribbon"],
                                "default": "cartoon",
                                "description": "Primary visualization style: 'cartoon' for secondary structure, 'surface' for molecular surface, 'sticks' for bonds, 'spheres' for atoms, 'ribbon' for backbone"
                            },
                            "chains": {"type": "array", "items": {"type": "string"}, "description": "Specific chains to display (e.g., ['A', 'B']). Leave empty for all chains."},
                            "residues": {"type": "array", "items": {"type": "string"}, "description": "Specific residues to highlight with special coloring (e.g., ['HIS64', 'ASP102'])"},
                            "width": {"type": "integer", "default": 800, "description": "Output image width in pixels (recommended: 800-2400 for publications)"},
                            "height": {"type": "integer", "default": 600, "description": "Output image height in pixels (recommended: 600-1800 for publications)"}
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
                ),
                Tool(
                    name="launch_pymol_gui",
                    description="🖥️ Launch interactive PyMOL GUI with real-time control. Supports XML-RPC for instant command execution, direct Python module integration, and script-based fallback. Perfect for interactive structure exploration.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_id": {"type": "string", "description": "Optional: ID of PDB structure file to load immediately upon launch. Leave empty to start with blank session."}
                        }
                    }
                ),
                Tool(
                    name="execute_pymol_command",
                    description="⚡ Execute PyMOL commands in real-time within active GUI session. Supports all PyMOL commands: visualization (show, hide, color), selection (select), analysis (distance, angle), and scripting commands.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "PyMOL command to execute (e.g., 'show cartoon', 'color red, chain A', 'select active_site, resn HIS+ASP+GLU', 'distance d1, resid 100, resid 200')"}
                        },
                        "required": ["command"]
                    }
                ),
                Tool(
                    name="load_structure_gui",
                    description="Load a protein structure in PyMOL GUI",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_id": {"type": "string", "description": "ID of the PDB structure file"},
                            "object_name": {"type": "string", "default": "structure", "description": "Name for the loaded object"}
                        },
                        "required": ["file_id"]
                    }
                ),
                Tool(
                    name="apply_gui_style",
                    description="Apply visualization style in PyMOL GUI",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "object_name": {"type": "string", "description": "Name of the loaded object"},
                            "style": {
                                "type": "string",
                                "enum": ["cartoon", "surface", "sticks", "spheres"],
                                "description": "Visualization style"
                            },
                            "color": {"type": "string", "default": "spectrum", "description": "Color scheme"}
                        },
                        "required": ["object_name", "style"]
                    }
                ),
                Tool(
                    name="highlight_residues_gui",
                    description="Highlight specific residues in PyMOL GUI",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "object_name": {"type": "string", "description": "Name of the loaded object"},
                            "residue_selections": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "PyMOL selection strings for residues to highlight"
                            },
                            "color": {"type": "string", "default": "red", "description": "Highlight color"}
                        },
                        "required": ["object_name", "residue_selections"]
                    }
                ),
                Tool(
                    name="get_pymol_gui_status",
                    description="Get status of PyMOL GUI session",
                    inputSchema={
                        "type": "object",
                        "properties": {}
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
                elif name == "launch_pymol_gui":
                    return await self._launch_pymol_gui(arguments)
                elif name == "execute_pymol_command":
                    return await self._execute_pymol_command(arguments)
                elif name == "load_structure_gui":
                    return await self._load_structure_gui(arguments)
                elif name == "apply_gui_style":
                    return await self._apply_gui_style(arguments)
                elif name == "highlight_residues_gui":
                    return await self._highlight_residues_gui(arguments)
                elif name == "get_pymol_gui_status":
                    return await self._get_pymol_gui_status(arguments)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error executing tool {name}: {str(e)}")]
    
    async def _upload_file(self, args: Dict[str, Any]) -> List[TextContent]:
        """Upload biological file to research workspace"""
        filename = args["filename"]
        content_b64 = args["content"]
        
        try:
            content = base64.b64decode(content_b64)
            file_id = await self.file_system.upload_file(filename, content)
            
            # Get file info for better response
            file_info = await self.file_system.get_file_info(file_id)
            bio_type = file_info.get('bio_type', 'Unknown') if file_info else 'Unknown'
            size = len(content)
            
            return [TextContent(
                type="text",
                text=f"✅ **{filename}** uploaded successfully!\n\n📄 **File Details:**\n• ID: `{file_id}`\n• Type: {bio_type}\n• Size: {size:,} bytes\n\n🔬 The file is now ready for analysis. Use tools like `calculate_pka`, `visualize_structure`, or `launch_pymol_gui` to begin research."
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"❌ **Upload failed:** {str(e)}\n\n💡 **Tips:**\n• Ensure content is properly base64 encoded\n• Check file format (PDB, FASTA, etc.)\n• Verify file size is reasonable"
            )]
    
    async def _list_files(self, args: Dict[str, Any]) -> List[TextContent]:
        """Browse uploaded biological files"""
        bio_type = args.get("bio_type")
        files = await self.file_system.list_files(bio_type)
        
        if not files:
            filter_text = f" of type '{bio_type}'" if bio_type else ""
            return [TextContent(
                type="text",
                text=f"📂 **No files found{filter_text}**\n\n💡 **Get started:**\n• Upload files using `upload_file`\n• Supported formats: PDB, FASTA, mmCIF, GenBank\n• Try example: upload a protein structure from RCSB PDB"
            )]
        
        type_emoji = {"structure": "🧬", "protein": "🔗", "dna": "🧬", "rna": "🧬", "small_molecule": "⚛️"}
        filter_text = f" ({bio_type} files)" if bio_type else ""
        result = f"📁 **Research Workspace{filter_text}** - {len(files)} file(s):\n\n"
        
        for file_info in files:
            emoji = type_emoji.get(file_info['bio_type'], "📄")
            result += f"{emoji} **{file_info['filename']}**\n"
            result += f"   🆔 ID: `{file_info['file_id']}`\n"
            result += f"   📊 Type: {file_info['bio_type'] or 'Unknown'} | Size: {file_info['size']:,} bytes\n"
            result += f"   📝 {file_info['summary']}\n"
            result += f"   ⏰ Uploaded: {file_info['upload_time']}\n\n"
        
        result += "🔬 **Available Actions:**\n• `calculate_pka` - Analyze pKa values\n• `visualize_structure` - Create images\n• `launch_pymol_gui` - Interactive exploration"
        
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
        """Advanced pKa analysis using PROPKA3"""
        file_id = args["file_id"]
        ph = args.get("ph", 7.0)
        chains = args.get("chains")
        residue_range = args.get("residue_range")
        
        # Get file path and info
        file_path = await self.file_system.get_file_path(file_id)
        if file_path is None:
            return [TextContent(
                type="text",
                text=f"❌ **File not found:** ID '{file_id}' doesn't exist\n\n💡 **Tip:** Use `list_files` to see available structures"
            )]
        
        file_info = await self.file_system.get_file_info(file_id)
        structure_name = file_info.get('filename', 'Unknown') if file_info else 'Unknown'
        
        if file_info and file_info.get("bio_type") != "structure":
            return [TextContent(
                type="text",
                text=f"⚠️ **Invalid file type:** '{structure_name}' is not a PDB structure\n\n🧪 **PROPKA requirements:**\n• PDB format (.pdb)\n• Protein structure with coordinates\n• Contains ionizable residues (ASP, GLU, HIS, CYS, TYR, LYS, ARG)"
            )]
        
        # Run PROPKA calculation with enhanced feedback
        try:
            result = await self.propka_tool.calculate_pka(
                file_path, ph, chains, residue_range
            )
            
            if not result["success"]:
                error_msg = result.get('error', 'Unknown error')
                return [TextContent(
                    type="text",
                    text=f"❌ **PROPKA calculation failed**\n\n**Error:** {error_msg}\n\n🔧 **Troubleshooting:**\n• Ensure PROPKA3 is installed: `pip install propka`\n• Check PDB file format and structure\n• Verify ionizable residues are present\n• Try with default parameters first"
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
            
            # Add biological interpretation
            output += f"\n🧬 **Biological Insights:**\n"
            if significant_shifts:
                output += "• Significant pKa shifts indicate **protein microenvironment effects**\n"
                output += "• Consider **electrostatic interactions** and **hydrogen bonding**\n"
            else:
                output += "• pKa values are **close to standard** - minimal environmental perturbation\n"
                output += "• Residues likely **surface-exposed** or in **typical environments**\n"
            
            if total_groups > 0:
                output += f"\n🔬 **Next Steps:**\n"
                output += "• Use `visualize_structure` to see ionizable residues\n"
                output += "• Try `launch_pymol_gui` for interactive exploration\n"
                output += "• Consider different pH values for protonation analysis\n"
            
            return [TextContent(type="text", text=output)]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"💥 **Calculation error:** {str(e)}\n\n🔧 **Common issues:**\n• PROPKA3 not installed\n• Invalid PDB format\n• No ionizable residues found\n• File permission issues"
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
    
    async def _launch_pymol_gui(self, args: Dict[str, Any]) -> List[TextContent]:
        """Launch PyMOL GUI for interactive visualization"""
        file_id = args.get("file_id")
        
        file_path = None
        if file_id:
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
            result = await self.pymol_tool.launch_gui_session(file_path)
            
            if not result["success"]:
                return [TextContent(
                    type="text",
                    text=f"Failed to launch PyMOL GUI: {result.get('error', 'Unknown error')}"
                )]
            
            output = f"**PyMOL GUI Launched Successfully**\n\n"
            output += f"• GUI Mode: {result.get('gui_mode', False)}\n"
            output += f"• Control Method: {result.get('control_mode', 'unknown')}\n"
            
            if result.get("rpc_port"):
                output += f"• XML-RPC Port: {result['rpc_port']} (Real-time execution enabled!)\n"
            
            if result.get("loaded_structure"):
                output += f"• Loaded structure: {result['loaded_structure']}\n"
            
            control_mode = result.get('control_mode', 'script')
            if control_mode == 'pymol_remote':
                output += "\n🚀 **Real-time execution enabled!** Commands will execute instantly via pymol-remote.\n"
            elif control_mode == 'xmlrpc':
                output += "\n🚀 **Real-time execution enabled!** Commands will execute instantly in PyMOL GUI.\n"
            elif control_mode == 'module':
                output += "\n⚡ **Direct module execution enabled!** Commands will execute directly.\n"
            else:
                output += "\n📝 **Script-based execution** - Commands will create script files for manual execution.\n"
                
                # Show pymol-remote error if available
                if result.get('pymol_remote_error'):
                    output += f"\n⚠️ **Note**: Real-time control unavailable - {result['pymol_remote_error']}\n"
                    output += "💡 **To enable real-time control**: Install pymol-remote with `pip install pymol-remote`\n"
            
            output += "\n**Available Commands:**\n"
            output += "• `execute_pymol_command` - Execute PyMOL commands\n"
            output += "• `load_structure_gui` - Load structures\n"
            output += "• `apply_gui_style` - Apply visualization styles\n"
            output += "• `highlight_residues_gui` - Highlight active sites\n"
            output += "• `get_pymol_gui_status` - Check session status\n"
            
            output += "\n💡 **Pro Tips:**\n"
            output += "• Use `show cartoon` for secondary structure\n"
            output += "• Try `color spectrum` for rainbow coloring\n"
            output += "• Select active sites with `select site, resn HIS+ASP+GLU`\n"
            
            return [TextContent(type="text", text=output)]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"❌ **Unexpected error:** {str(e)}\n\n🔍 **Debug info:** Check PyMOL installation and system logs"
            )]
    
    async def _execute_pymol_command(self, args: Dict[str, Any]) -> List[TextContent]:
        """Execute PyMOL command in GUI session"""
        command = args["command"]
        
        try:
            result = await self.pymol_tool.execute_pymol_command(command)
            
            if not result["success"]:
                return [TextContent(
                    type="text",
                    text=f"Command failed: {result.get('error', 'Unknown error')}"
                )]
            
            execution_method = result.get("execution_method", "unknown")
            
            if execution_method == "pymol_remote":
                output = f"**🚀 PyMOL Command Executed in Real-Time!**\n\n"
                output += f"• Command: `{result['command']}`\n"
                output += f"• Execution: pymol_remote (instant)\n"
                output += f"• Status: ✅ Success\n"
                if result.get("output"):
                    output += f"• Result: {result['output']}\n"
            elif execution_method == "xmlrpc":
                output = f"**🚀 PyMOL Command Executed in Real-Time!**\n\n"
                output += f"• Command: `{result['command']}`\n"
                output += f"• Execution: XML-RPC (instant)\n"
                output += f"• Status: ✅ Success\n"
            elif execution_method == "module":
                output = f"**⚡ PyMOL Command Executed Directly!**\n\n"
                output += f"• Command: `{result['command']}`\n"
                output += f"• Execution: Python Module (direct)\n"
                output += f"• Status: ✅ Success\n"
            else:
                output = f"**📝 PyMOL Command Script Created**\n\n"
                output += f"• Command: `{result['command']}`\n"
                output += f"• Execution: Script-based\n"
                output += f"• Status: Script ready\n"
            
            if result.get("manual_execution_needed"):
                output += f"\n**Instructions:**\n"
                output += f"In PyMOL GUI, execute: `{result['instructions']}`\n"
                if result.get("script_file"):
                    output += f"Script saved to: {result['script_file']}\n"
            
            if result.get("output"):
                output += f"\n**Output:**\n{result['output']}"
            
            return [TextContent(type="text", text=output)]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error executing command: {str(e)}"
            )]
    
    async def _load_structure_gui(self, args: Dict[str, Any]) -> List[TextContent]:
        """Load structure in PyMOL GUI"""
        file_id = args["file_id"]
        object_name = args.get("object_name", "structure")
        
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
            result = await self.pymol_tool.load_structure_in_gui(file_path, object_name)
            
            if not result["success"]:
                return [TextContent(
                    type="text",
                    text=f"Failed to load structure: {result.get('error', 'Unknown error')}"
                )]
            
            execution_method = result.get("execution_method", "script")
            
            if execution_method in ["xmlrpc", "module"]:
                output = f"**🚀 Structure Loaded in Real-Time!**\n\n"
                output += f"• Structure: {result.get('loaded_structure', file_path)}\n"
                output += f"• Object name: {result.get('object_name', object_name)}\n"
                output += f"• Execution: {execution_method} (real-time)\n"
                output += f"• Commands executed: {result.get('commands_executed', 0)}/{result.get('total_commands', 0)}\n"
            else:
                output = f"**📝 Structure Loading Script Created**\n\n"
                output += f"• Structure: {result.get('loaded_structure', file_path)}\n"
                output += f"• Object name: {result.get('object_name', object_name)}\n"
            
            if result.get("instructions"):
                output += f"\n**Instructions:**\n"
                output += f"In PyMOL GUI, execute: `{result['instructions']}`\n"
                output += f"Script saved to: {result['script_file']}\n"
                
                output += f"\n**Manual Commands (alternative):**\n"
                for cmd in result.get('manual_commands', []):
                    output += f"• `{cmd}`\n"
            
            return [TextContent(type="text", text=output)]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error loading structure: {str(e)}"
            )]
    
    async def _apply_gui_style(self, args: Dict[str, Any]) -> List[TextContent]:
        """Apply visualization style in PyMOL GUI"""
        object_name = args["object_name"]
        style = args["style"]
        color = args.get("color", "spectrum")
        
        try:
            result = await self.pymol_tool.apply_visualization_style(object_name, style, color)
            
            if not result["success"]:
                return [TextContent(
                    type="text",
                    text=f"Failed to apply style: Style application failed"
                )]
            
            output = f"**Visualization Style Script Created**\n\n"
            output += f"• Object: {result['object_name']}\n"
            output += f"• Style: {result['style']}\n"
            output += f"• Color: {result['color']}\n"
            
            if result.get("instructions"):
                output += f"\n**Instructions:**\n"
                output += f"In PyMOL GUI, execute: `{result['instructions']}`\n"
                output += f"Script saved to: {result['script_file']}\n"
                
                output += f"\n**Manual Commands (alternative):**\n"
                for cmd in result.get('manual_commands', []):
                    output += f"• `{cmd}`\n"
            
            return [TextContent(type="text", text=output)]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error applying style: {str(e)}"
            )]
    
    async def _highlight_residues_gui(self, args: Dict[str, Any]) -> List[TextContent]:
        """Highlight residues in PyMOL GUI"""
        object_name = args["object_name"]
        residue_selections = args["residue_selections"]
        color = args.get("color", "red")
        
        try:
            result = await self.pymol_tool.highlight_residues_in_gui(object_name, residue_selections, color)
            
            if not result["success"]:
                return [TextContent(
                    type="text",
                    text=f"Failed to highlight residues: Highlighting failed"
                )]
            
            output = f"**Residue Highlighting Script Created**\n\n"
            output += f"• Object: {result['object_name']}\n"
            output += f"• Selections highlighted: {len(result['highlighted_selections'])}\n"
            output += f"• Color: {result['color']}\n"
            
            for i, selection in enumerate(result['highlighted_selections']):
                output += f"  - Selection {i+1}: {selection}\n"
            
            if result.get("instructions"):
                output += f"\n**Instructions:**\n"
                output += f"In PyMOL GUI, execute: `{result['instructions']}`\n"
                output += f"Script saved to: {result['script_file']}\n"
                
                output += f"\n**Manual Commands (alternative):**\n"
                for cmd in result.get('manual_commands', []):
                    output += f"• `{cmd}`\n"
            
            return [TextContent(type="text", text=output)]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error highlighting residues: {str(e)}"
            )]
    
    async def _get_pymol_gui_status(self, args: Dict[str, Any]) -> List[TextContent]:
        """Get PyMOL GUI status"""
        try:
            result = await self.pymol_tool.get_gui_status()
            
            output = f"**PyMOL GUI Status**\n\n"
            output += f"• GUI Active: {result['gui_active']}\n"
            output += f"• PyMOL Available: {result['pymol_available']}\n"
            output += f"• Control Method: {result.get('control_method', 'none')}\n"
            output += f"• Real-time Execution: {'✅ Yes' if result.get('real_time_execution') else '❌ No'}\n"
            
            if result.get('xmlrpc_available'):
                output += f"• XML-RPC Server: ✅ Active (port {result.get('xmlrpc_port')})\n"
            elif result.get('module_available'):
                output += f"• Python Module: ✅ Available\n"
            elif result['gui_active']:
                output += f"• Script Fallback: ✅ Available\n"
            
            output += f"• PyMOL Executable: {result['pymol_executable']}\n"
            
            if result['gui_active'] and result.get('process_id'):
                output += f"• Process ID: {result['process_id']}\n"
            
            if not result['gui_active']:
                output += "\n**Note:** No active GUI session. Use `launch_pymol_gui` to start one."
            elif result.get('real_time_execution'):
                output += "\n🚀 **Real-time command execution is enabled!**"
            else:
                output += "\n📝 **Script-based execution is available.**"
            
            return [TextContent(type="text", text=output)]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error getting GUI status: {str(e)}"
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