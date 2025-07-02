# 📁 File Upload Instructions for Bio-MCP

## ⚠️ Important: MCP Protocol Limitation

**Files CANNOT be uploaded directly through the host application.** The Model Context Protocol (MCP) does not provide mechanisms for file transfer from host to server. 

## 🔧 Proper File Upload Methods

### 1. **Direct Workspace Placement** (Recommended)
```bash
# Copy files directly to Bio-MCP workspace
cp your_protein.pdb bio_data/structures/
cp your_sequence.fasta bio_data/sequences/
```

**Workspace Structure:**
```
bio_data/
├── structures/         # PDB, mmCIF files
├── sequences/          # FASTA, GenBank files  
├── analysis/           # Analysis results
└── visualizations/     # Generated images
```

### 2. **Using MCP-Compatible Applications**
- Use applications that properly implement MCP file transfer protocols
- Upload via base64 encoding through MCP client tools
- Ensure proper MCP tool integration

### 3. **Through AI Assistant Guidance**
- Ask: "How do I upload a protein structure for analysis?"
- AI will guide you through proper upload procedures
- AI can help identify the correct file format and location

## 🚫 What NOT to Do

❌ **Don't try to upload through host commands:**
```bash
bio-mcp> upload /path/to/file.pdb  # This will fail
```

❌ **Don't expect drag-and-drop in host interface**

❌ **Don't use standard file upload APIs through host**

## ✅ What TO Do

✅ **Use the upload-help command:**
```bash
bio-mcp> upload-help
```

✅ **Place files in correct workspace directories**

✅ **Verify uploads with files command:**
```bash
bio-mcp> files
```

✅ **Ask AI for help:**
```bash
bio-mcp> chat How do I upload a PDB file for analysis?
```

## 🔬 After Successful Upload

Once files are properly uploaded to the workspace:

1. **Verify Upload:**
   ```bash
   bio-mcp> files
   ```

2. **Start Analysis:**
   ```bash
   bio-mcp> chat analyze my protein structure
   bio-mcp> chat calculate pKa values for my protein
   bio-mcp> chat create a visualization of the structure
   ```

3. **Use Specific Tools:**
   - `calculate_pka` - pKa analysis with PROPKA
   - `visualize_structure` - Create publication-quality images
   - `launch_pymol_gui` - Interactive structure exploration

## 🤖 AI Assistant Instructions

When users ask about file uploads, AI assistants should:

1. **Explain the limitation:** MCP doesn't support host-to-server file transfer
2. **Provide proper instructions:** Direct workspace placement or MCP-compatible tools
3. **Guide to alternatives:** Help users understand correct upload procedures
4. **Offer analysis help:** Once files are uploaded, assist with biological analysis

## 📞 Support

If you encounter issues with file uploads:

1. Check the `upload-help` command output
2. Verify workspace directory structure exists
3. Ensure file formats are supported (PDB, FASTA, mmCIF, GenBank)
4. Ask the AI assistant for personalized guidance