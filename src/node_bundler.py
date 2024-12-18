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

def zip_filtered_directory(input_dir, zip_path):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(input_dir):
            for file in files:
                filepath = os.path.join(root, file)
                if should_include_file(filepath, input_dir):
                    arcname = os.path.relpath(filepath, start=input_dir)
                    zipf.write(filepath, arcname)

def write_direct_listings(input_dir, output_file):
    # Write all included files as plain text with headers
    included_files = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            filepath = os.path.join(root, file)
            if should_include_file(filepath, input_dir):
                rel_path = os.path.relpath(filepath, start=input_dir)
                included_files.append(rel_path)
    
    # Sort files by name to have a deterministic order
    included_files.sort()

    with open(output_file, "w") as out:
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
        Please consider that these would have otherwise been in a ZIP. You can treat each 
        "## File: filename" header as a separate file boundary. The contents below each header line 
        is that file’s code.

        To use this in the chat environment:
        1. Imagine these files are restored into a directory structure according to their paths.
        2. Review and potentially improve the code. Ask any follow-up questions if needed.
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

    if no_encode:
        # Write all included files directly to output_text_file with headers
        write_direct_listings(input_directory, output_text_file)
        print(f"Included files have been listed directly in {output_text_file}.")
    else:
        # Perform original zip + base64 encoding
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "filtered_app.zip")
            zip_filtered_directory(input_directory, zip_path)

            # Read and base64-encode the zip
            with open(zip_path, "rb") as f:
                zip_data = f.read()
                encoded = base64.b64encode(zip_data).decode('utf-8')

        # Updated instructions for efficient AI parsing
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

        with open(output_text_file, "w") as out:
            out.write(encoded)
            out.write(instructions)

        print(f"Filtered files have been successfully bundled and saved to {output_text_file}.")
        print("Copy the entire contents of that file and paste it into the chat environment.")
        print("Follow the instructions at the bottom of the file to interpret and improve the code.")
