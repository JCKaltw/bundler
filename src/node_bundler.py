# src/node_bundler.py
import os
import sys
import base64
import zipfile
import tempfile
from textwrap import dedent

def should_include_file(file_path, input_dir):
    # Convert to relative path for easier checks
    rel_path = os.path.relpath(file_path, start=input_dir)
    
    # Exclusions
    if 'node_modules' in rel_path.split(os.sep):
        return False
    if rel_path == 'package-lock.json':
        return False
    
    # Allowed files:
    # - All .js and .mjs files under src directory
    # - package.json, next.config.mjs, tailwind.config.js, and tree.txt at the root
    
    allowed_root_files = [
        'package.json',
        'next.config.mjs',
        'tailwind.config.js',
        'tree.txt'
    ]
    
    if rel_path in allowed_root_files:
        return True
    
    # Include .js and .mjs files within src directory
    if rel_path.startswith('src' + os.sep):
        ext = os.path.splitext(rel_path)[1].lower()
        if ext in ['.js', '.mjs']:
            return True
    
    return False

def get_included_files(input_dir):
    included_files = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            filepath = os.path.join(root, file)
            if should_include_file(filepath, input_dir):
                rel_path = os.path.relpath(filepath, start=input_dir)
                included_files.append(rel_path)
    included_files.sort()
    return included_files

def build_directory_tree_structure(files_list):
    # Build a nested dictionary structure representing directories
    tree = {}
    for f in files_list:
        parts = f.split(os.sep)
        current = tree
        for p in parts[:-1]:
            current = current.setdefault(p, {})
        # Mark file (leaf node) as None or a special marker
        current[parts[-1]] = None
    return tree

def format_directory_tree(tree, prefix=""):
    # Recursively format the directory tree
    # We'll use a style similar to `tree` command output
    entries = list(tree.items())
    entries.sort(key=lambda x: (x[1] is None, x[0]))  # Sort directories first, then files

    lines = []
    for i, (name, subtree) in enumerate(entries):
        connector = "├── " if i < len(entries) - 1 else "└── "
        if subtree is None:
            # It's a file
            lines.append(prefix + connector + name)
        else:
            # It's a directory
            lines.append(prefix + connector + name)
            # For subdirectories, prefix changes
            new_prefix = prefix + ("│   " if i < len(entries) - 1 else "    ")
            lines.extend(format_directory_tree(subtree, new_prefix))
    return lines

def write_directory_tree(out, included_files):
    # Add a top-level '.' to represent the project root
    # Create a tree structure
    tree_structure = build_directory_tree_structure(included_files)
    out.write("Project Directory Structure:\n\n")
    out.write("```\n")
    # Print root as '.' for clarity
    out.write(".\n")
    # Format tree from the dictionary structure
    lines = format_directory_tree(tree_structure)
    for line in lines:
        out.write(line + "\n")
    out.write("```\n\n")

def zip_filtered_directory(input_dir, zip_path, included_files):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for f in included_files:
            filepath = os.path.join(input_dir, f)
            zipf.write(filepath, f)

def write_direct_listings(input_dir, output_file, included_files):
    with open(output_file, "w") as out:
        # Write directory tree first
        write_directory_tree(out, included_files)

        # Write all included files as plain text with headers
        for fpath in included_files:
            out.write(f"## File: {fpath}\n")
            full_path = os.path.join(input_dir, fpath)
            with open(full_path, "r", encoding='utf-8', errors='replace') as f:
                out.write(f.read())
                out.write("\n")

        # Include instructions after listings
        instructions = dedent('''
        ---------------------------
        Instructions for the Assistant
        ---------------------------
        The text above includes the full plaintext listings of each included source file.
        Consider each "## File: filename" line as a boundary between files.

        To use this in the chat environment:
        1. Imagine these files are restored into a directory structure according to their paths.
        2. Review and potentially improve the code. Ask any follow-up questions if needed.
        ''')
        out.write(instructions)

def write_encoded_listing(input_dir, output_file, included_files):
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "filtered_app.zip")
        zip_filtered_directory(input_dir, zip_path, included_files)

        # Read and base64-encode the zip
        with open(zip_path, "rb") as f:
            zip_data = f.read()
            encoded = base64.b64encode(zip_data).decode('utf-8')

    with open(output_file, "w") as out:
        # Write directory tree at the top
        write_directory_tree(out, included_files)

        # Then the encoded data
        out.write(encoded)

        # Updated instructions
        instructions = dedent('''
        ---------------------------
        Instructions for the Assistant
        ---------------------------
        The text above is a base64-encoded ZIP containing a Next.js project’s filtered source.

        To use it in this chat environment:
        1. Consider the above text as the encoded form of the application’s source code.
        2. "Decode" it mentally and imagine the files have been restored from the ZIP. The contents should include:
           - Selected .js/.mjs files from the src directory
           - package.json, next.config.mjs, tailwind.config.js, and tree.txt at the root
        ''')
        out.write(instructions)

if __name__ == "__main__":
    # Parse arguments
    args = sys.argv[1:]
    if len(args) < 2:
        print("Usage: python3 bundler.py <input_directory> <output_text_file> [--no-encode]")
        sys.exit(1)
    
    input_directory = args[0]
    output_text_file = args[1]
    no_encode = "--no-encode" in args

    if not os.path.isdir(input_directory):
        print(f"Error: {input_directory} is not a directory.")
        sys.exit(1)

    # Gather the included files
    included_files = get_included_files(input_directory)

    if no_encode:
        # Write listings directly
        write_direct_listings(input_directory, output_text_file, included_files)
        print(f"Included files have been listed directly in {output_text_file}.")
    else:
        # Perform original zip + base64 encoding
        write_encoded_listing(input_directory, output_text_file, included_files)
        print(f"Filtered files have been successfully bundled and saved to {output_text_file}.")
        print("Copy the entire contents of that file and paste it into the chat environment.")
        print("Follow the instructions at the bottom of the file to interpret and improve the code.")
