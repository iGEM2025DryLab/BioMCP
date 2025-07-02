# 🧬 Bio-MCP Usage Guide

## 📁 File Upload Best Practices

### ✅ **Recommended: Use Bio-MCP CLI**

The bio-mcp CLI provides the proper way to upload and manage biological files:

```bash
# Start bio-mcp in interactive mode
python bio_mcp.py interactive

# Upload a protein structure
bio-mcp> upload /path/to/protein.pdb

# Upload a sequence file
bio-mcp> upload /path/to/sequence.fasta

# List uploaded files
bio-mcp> files

# Analyze uploaded files
bio-mcp> chat analyze my protein structure
bio-mcp> chat calculate pKa values for residues
```

### 🔧 **Why Use CLI Upload?**

1. **Automatic Processing**: Files are automatically categorized by biological type
2. **Base64 Encoding**: Handles proper encoding for MCP protocol
3. **File Validation**: Checks file formats and provides helpful errors
4. **Integration**: Seamless integration with analysis tools
5. **Metadata Generation**: Creates file IDs and metadata for tracking

### ❌ **Avoid: Direct Upload to AI Applications**

Don't upload files directly to applications like Claude Desktop:

```bash
# DON'T DO THIS:
# - Drag files into Claude Desktop
# - Use Claude's file upload feature
# - Copy/paste file contents into chat
```

**Why not?**
- Files won't be available to bio-mcp tools
- No automatic biological file processing
- Missing file IDs needed for analysis
- No integration with PyMOL, PROPKA, etc.

## 🔬 **Analysis Workflow**

### 1. **Upload Files via CLI**
```bash
bio-mcp> upload protein.pdb
✅ protein.pdb uploaded successfully!
📄 File Details:
• ID: protein_abc123
• Type: structure
• Size: 125,432 bytes
```

### 2. **Verify Upload**
```bash
bio-mcp> files
🧬 Research Workspace - 1 file(s):
🧪 protein.pdb
   🆔 ID: protein_abc123
   📊 Type: structure | Size: 125,432 bytes
```

### 3. **Analyze with AI**
```bash
bio-mcp> chat analyze this protein structure
# AI will use the uploaded file for analysis

bio-mcp> chat calculate pKa values at pH 7.4
# AI will use PROPKA tool with your file

bio-mcp> chat create a visualization
# AI will use PyMOL to create images
```

## 🛠️ **Available Tools**

Once files are uploaded via CLI, these tools become available:

### **Structure Analysis**
- `calculate_pka` - pKa calculations with PROPKA3
- `visualize_structure` - Publication-quality images
- `launch_pymol_gui` - Interactive molecular visualization
- `analyze_structure_pymol` - Structural analysis

### **File Operations**
- `list_files` - Browse uploaded files
- `read_file_content` - Read file contents
- `get_file_info` - File metadata
- `find_residues` - Locate specific amino acids

### **Sequence Tools**
- `get_sequence_range` - Extract sequence segments
- `search_file_content` - Pattern matching in files

## 🎯 **Examples**

### **Complete Protein Analysis Workflow**
```bash
# 1. Upload structure
bio-mcp> upload 1abc.pdb

# 2. Chat analysis
bio-mcp> chat What's the structure and function of this protein?

# 3. pKa analysis
bio-mcp> chat Calculate pKa values for all ionizable residues

# 4. Visualization
bio-mcp> chat Create a cartoon representation highlighting active site residues

# 5. Interactive exploration
bio-mcp> chat Launch PyMOL for interactive analysis
```

### **Sequence Analysis**
```bash
# Upload sequence
bio-mcp> upload sequence.fasta

# Analyze
bio-mcp> chat Analyze this protein sequence for functional domains
```

## 💡 **Tips**

1. **File Naming**: Use descriptive names (e.g., `lysozyme_1hel.pdb`)
2. **File Organization**: CLI automatically organizes by type
3. **Multiple Files**: Upload related files for comparative analysis
4. **AI Assistance**: Let AI guide you through complex analyses
5. **Interactive Mode**: Use PyMOL GUI for detailed exploration

## 🚨 **Troubleshooting**

### **Upload Issues**
```bash
bio-mcp> upload missing_file.pdb
File not found: missing_file.pdb

# Solution: Check file path and existence
```

### **No Tools Available**
```bash
bio-mcp> chat analyze structure
Error: No files uploaded

# Solution: Upload files first via CLI
```

### **Connection Issues**
```bash
bio-mcp> health
# Check if MCP server is running properly
```

## 📞 **Getting Help**

- Use `help` command in CLI
- Ask AI: "How do I upload a protein structure?"
- Check `status` command for system health
- Review file formats: PDB, FASTA, mmCIF, GenBank