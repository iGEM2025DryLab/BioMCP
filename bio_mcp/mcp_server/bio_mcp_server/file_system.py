import os
import sys
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import aiofiles
import re

@dataclass
class FileMetadata:
    """Metadata for stored files"""
    filename: str
    file_id: str
    size: int
    file_type: str
    upload_time: str
    checksum: str
    bio_type: Optional[str] = None  # 'protein', 'dna', 'rna', 'structure'
    additional_info: Dict[str, Any] = None

    def __post_init__(self):
        if self.additional_info is None:
            self.additional_info = {}

class BioFileSystem:
    """Smart file system for biological data with metadata and efficient access"""
    
    def __init__(self, base_path: str = None):
        if base_path is None:
            # Use absolute path in the project directory
            project_root = Path(__file__).parent.parent.parent
            base_path = project_root / "bio_data"
        
        self.base_path = Path(base_path)
        try:
            self.base_path.mkdir(exist_ok=True)
        except OSError as e:
            # If we can't create in the intended location, fall back to home directory
            fallback_path = Path.home() / ".bio_mcp_data"
            fallback_path.mkdir(exist_ok=True)
            print(f"Warning: Using fallback data directory: {fallback_path}", file=sys.stderr)
            
            # Copy existing data if the original path exists and has data
            original_path = Path(base_path)
            if original_path.exists() and (original_path / "metadata.json").exists():
                import shutil
                try:
                    shutil.copytree(original_path, fallback_path, dirs_exist_ok=True)
                    print(f"Copied existing data to fallback location", file=sys.stderr)
                except Exception as copy_err:
                    print(f"Warning: Could not copy existing data: {copy_err}", file=sys.stderr)
            
            self.base_path = fallback_path
        
        # Create subdirectories
        self.structures_path = self.base_path / "structures"
        self.sequences_path = self.base_path / "sequences"
        self.analysis_path = self.base_path / "analysis"
        self.visualizations_path = self.base_path / "visualizations"
        
        for path in [self.structures_path, self.sequences_path, self.analysis_path, self.visualizations_path]:
            path.mkdir(exist_ok=True)
        
        self.metadata_file = self.base_path / "metadata.json"
        self._load_metadata()
    
    def _load_metadata(self):
        """Load file metadata from disk"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                data = json.load(f)
                self.metadata = {k: FileMetadata(**v) for k, v in data.items()}
        else:
            self.metadata = {}
    
    def _save_metadata(self):
        """Save file metadata to disk"""
        data = {k: asdict(v) for k, v in self.metadata.items()}
        with open(self.metadata_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _generate_file_id(self, filename: str, content: bytes) -> str:
        """Generate unique file ID based on filename and content hash"""
        content_hash = hashlib.md5(content).hexdigest()[:8]
        return f"{Path(filename).stem}_{content_hash}"
    
    def _detect_bio_type(self, filename: str, content: str) -> Optional[str]:
        """Detect biological file type from filename and content"""
        filename_lower = filename.lower()
        
        if filename_lower.endswith(('.pdb', '.cif', '.mmcif')):
            return 'structure'
        elif filename_lower.endswith(('.fasta', '.fa', '.fas')):
            # Check if DNA/RNA or protein
            if re.search(r'[ATCGU]{20,}', content.upper()):
                return 'dna' if 'T' in content.upper() else 'rna'
            else:
                return 'protein'
        elif filename_lower.endswith(('.sdf', '.mol', '.mol2')):
            return 'small_molecule'
        
        return None
    
    def _get_file_path(self, file_id: str, bio_type: str) -> Path:
        """Get appropriate file path based on bio type"""
        if bio_type == 'structure':
            return self.structures_path / f"{file_id}.pdb"
        elif bio_type in ['dna', 'rna', 'protein']:
            return self.sequences_path / f"{file_id}.fasta"
        elif bio_type == 'small_molecule':
            return self.structures_path / f"{file_id}.sdf"
        else:
            return self.base_path / f"{file_id}.dat"
    
    async def upload_file(self, filename: str, content: bytes) -> str:
        """Upload file and return file ID"""
        content_str = content.decode('utf-8', errors='ignore')
        file_id = self._generate_file_id(filename, content)
        bio_type = self._detect_bio_type(filename, content_str)
        
        # Save file
        file_path = self._get_file_path(file_id, bio_type or 'unknown')
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        # Extract additional info based on bio type
        additional_info = {}
        if bio_type == 'structure':
            additional_info = await self._extract_pdb_info(content_str)
        elif bio_type in ['dna', 'rna', 'protein']:
            additional_info = await self._extract_sequence_info(content_str)
        
        # Create metadata
        metadata = FileMetadata(
            filename=filename,
            file_id=file_id,
            size=len(content),
            file_type=Path(filename).suffix.lower(),
            upload_time=datetime.now().isoformat(),
            checksum=hashlib.md5(content).hexdigest(),
            bio_type=bio_type,
            additional_info=additional_info
        )
        
        self.metadata[file_id] = metadata
        self._save_metadata()
        
        return file_id
    
    async def _extract_pdb_info(self, content: str) -> Dict[str, Any]:
        """Extract basic information from PDB file"""
        info = {}
        lines = content.split('\n')
        
        for line in lines:
            if line.startswith('HEADER'):
                info['header'] = line[10:50].strip()
                info['pdb_id'] = line[62:66].strip()
            elif line.startswith('TITLE'):
                info['title'] = line[10:].strip()
            elif line.startswith('COMPND'):
                if 'compound' not in info:
                    info['compound'] = []
                info['compound'].append(line[10:].strip())
            elif line.startswith('ATOM'):
                if 'chains' not in info:
                    info['chains'] = set()
                info['chains'].add(line[21])
                if 'residue_count' not in info:
                    info['residue_count'] = 0
                info['residue_count'] += 1
        
        if 'chains' in info:
            info['chains'] = list(info['chains'])
        
        return info
    
    async def _extract_sequence_info(self, content: str) -> Dict[str, Any]:
        """Extract basic information from FASTA file"""
        info = {'sequences': []}
        sequences = content.split('>')
        
        for seq in sequences[1:]:  # Skip first empty element
            lines = seq.strip().split('\n')
            if lines:
                header = lines[0]
                sequence = ''.join(lines[1:])
                info['sequences'].append({
                    'header': header,
                    'length': len(sequence),
                    'sequence_preview': sequence[:50] + ('...' if len(sequence) > 50 else '')
                })
        
        info['total_sequences'] = len(info['sequences'])
        return info
    
    async def list_files(self, bio_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List files with optional filtering by bio type"""
        files = []
        for file_id, metadata in self.metadata.items():
            if bio_type is None or metadata.bio_type == bio_type:
                files.append({
                    'file_id': file_id,
                    'filename': metadata.filename,
                    'size': metadata.size,
                    'bio_type': metadata.bio_type,
                    'upload_time': metadata.upload_time,
                    'summary': self._get_file_summary(metadata)
                })
        
        return sorted(files, key=lambda x: x['upload_time'], reverse=True)
    
    def _get_file_summary(self, metadata: FileMetadata) -> str:
        """Generate human-readable file summary"""
        if metadata.bio_type == 'structure':
            chains = metadata.additional_info.get('chains', [])
            return f"Structure with {len(chains)} chain(s): {', '.join(chains)}"
        elif metadata.bio_type in ['dna', 'rna', 'protein']:
            seq_count = metadata.additional_info.get('total_sequences', 0)
            return f"{seq_count} sequence(s)"
        else:
            return f"{metadata.bio_type or 'Unknown'} file"
    
    async def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed file information"""
        if file_id not in self.metadata:
            return None
        
        metadata = self.metadata[file_id]
        return {
            'file_id': file_id,
            'filename': metadata.filename,
            'size': metadata.size,
            'file_type': metadata.file_type,
            'bio_type': metadata.bio_type,
            'upload_time': metadata.upload_time,
            'checksum': metadata.checksum,
            'additional_info': metadata.additional_info,
            'summary': self._get_file_summary(metadata)
        }
    
    async def read_file_content(self, file_id: str, start_line: int = 0, max_lines: int = 1000) -> Optional[str]:
        """Read file content with optional line range"""
        if file_id not in self.metadata:
            return None
        
        metadata = self.metadata[file_id]
        file_path = self._get_file_path(file_id, metadata.bio_type or 'unknown')
        
        if not file_path.exists():
            return None
        
        async with aiofiles.open(file_path, 'r') as f:
            lines = await f.readlines()
            end_line = min(start_line + max_lines, len(lines))
            return ''.join(lines[start_line:end_line])
    
    async def search_file_content(self, file_id: str, pattern: str, max_matches: int = 100) -> Optional[List[Dict[str, Any]]]:
        """Search for pattern in file content"""
        if file_id not in self.metadata:
            return None
        
        metadata = self.metadata[file_id]
        file_path = self._get_file_path(file_id, metadata.bio_type or 'unknown')
        
        if not file_path.exists():
            return None
        
        matches = []
        async with aiofiles.open(file_path, 'r') as f:
            lines = await f.readlines()
            for line_num, line in enumerate(lines):
                if re.search(pattern, line, re.IGNORECASE):
                    matches.append({
                        'line_number': line_num + 1,
                        'content': line.strip(),
                        'match': re.search(pattern, line, re.IGNORECASE).group() if re.search(pattern, line, re.IGNORECASE) else ''
                    })
                    if len(matches) >= max_matches:
                        break
        
        return matches
    
    async def get_file_path(self, file_id: str) -> Optional[Path]:
        """Get actual file path for external tools"""
        if file_id not in self.metadata:
            return None
        
        metadata = self.metadata[file_id]
        file_path = self._get_file_path(file_id, metadata.bio_type or 'unknown')
        
        return file_path if file_path.exists() else None