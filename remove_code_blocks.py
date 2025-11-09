#!/usr/bin/env python3
"""
Script to remove Python code blocks from Markdown files in backend/agents directory.
"""

import re
import os
from pathlib import Path

def remove_python_code_blocks(file_path):
    """Remove Python code blocks from a Markdown file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match Python code blocks
    # This matches ```python ... ``` or ``` ... ``` blocks
    pattern = r'```(?:python)?\n(.*?)```'
    
    # Remove the code blocks (including the content inside)
    updated_content = re.sub(pattern, '```', content, flags=re.DOTALL)
    
    # Clean up any empty code blocks left behind
    updated_content = updated_content.replace('```\n```', '')
    updated_content = updated_content.replace('```\r\n```\r\n', '')
    
    # Write the updated content back to the file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print(f"Removed Python code blocks from: {file_path}")

def main():
    """Main function to process all MD files in backend/agents."""
    backend_agents_dir = Path("backend/agents")
    
    if not backend_agents_dir.exists():
        print(f"Directory {backend_agents_dir} does not exist!")
        return
    
    # Find all Markdown files in the directory and subdirectories
    md_files = list(backend_agents_dir.rglob("*.md"))
    
    print(f"Found {len(md_files)} Markdown files to process...")
    
    for md_file in md_files:
        print(f"Processing: {md_file}")
        remove_python_code_blocks(md_file)
    
    print("Done! Python code blocks have been removed from all Markdown files.")

if __name__ == "__main__":
    main()