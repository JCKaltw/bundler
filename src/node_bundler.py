# src/node_bundler.py
import os
import sys
import base64
import zipfile
import tempfile
from textwrap import dedent

def should_include_file(file_path, input_dir, user_extensions=None, language='node'):
    """
    Decide if file_path should be included based on:
      1. Exclusions: node_modules, .next, package-lock.json
      2. If language='node' (default):
           - Include ONLY 'package.json' at the root (if present).
           - Include any file within 'src/' (recursively) that matches the extension list 
             (defaulting to ['js','mjs','jsx'] if none provided).
      3. If language='none':
           - Ignore 'package.json' root file.
           - Include any file (from any path) that matches the extension list (if provided),
             e.g. .json files. If none provided, likely includes nothing.
    """
    rel_path = os.path.relpath(file_path, start=input_dir)
    path_parts = rel_path.split(os.sep)

    # -- 1. Exclusion rules
    if 'node_modules' in path_parts:
        return False
    if '.next' in path_parts:
        return False
    if rel_path == 'package-lock.json':
        return False

    # -- 2. If language='node'
    if language == 'node':
        # By default, if user hasn't provided an --extension-list, we use these
        if not user_extensions:
            user_extensions = ['js','mjs','jsx']
        # Normalize them
        user_extensions = [ext.lower() for ext in user_extensions]

        # If exactly 'package.json' at the root
        if rel_path == 'package.json':
            return True
        
        # Otherwise, only files under 'src/' that match the extension list
        if rel_path.startswith('src' + os.sep):
            _, ext = os.path.splitext(rel_path)
            ext = ext.lower().lstrip('.')  # e.g. "js"
            return ext in user_extensions

        # If we reach here, we skip
        return False

    # -- 3. If language='none'
    elif language == 'none':
        # If user hasn't provided any extension list, default to empty => no files
        if not user_extensions:
            user_extensions = []
        user_extensions = [ext.lower() for ext in user_extensions]

        # We do NOT include package.json from the root
        # Instead, we include files from anywhere if extension matches
        _, ext = os.path.splitext(rel_path)
        ext = ext.lower().lstrip('.')  # e.g. "json"
        return ext in user_extensions

    # If some other language is passed, we can either mimic 'node' or do nothing special.
    # We'll mimic 'node' logic as a fallback.
    else:
        if not user_extensions:
            user_extensions = ['js','mjs','jsx']
        user_extensions = [ext.lower() for ext in user_extensions]

        # If exactly 'package.json' at the root
        if rel_path == 'package.json':
            return True
        
        # Otherwise, only files under 'src/' that match the extension list
        if rel_path.startswith('src' + os.sep):
            _, ext = os.path.splitext(rel_path)
            ext = ext.lower().lstrip('.')  # e.g. "js"
            return ext in user_extensions

        return False

def get_included_files(input_dir, user_extensions=None, language='node'):
    included_files = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            filepath = os.path.join(root, file)
            if should_include_file(filepath, input_dir, user_extensions, language):
                rel_path = os.path.relpath(filepath, start=input_dir)
                included_files.append(rel_path)
    included_files.sort()
    return included_files

def build_directory_tree_structure(files_list):
    tree = {}
    for f in files_list:
        parts = f.split(os.sep)
        current = tree
        for p in parts[:-1]:
            current = current.setdefault(p, {})
        current[parts[-1]] = None
    return tree

def format_directory_tree(tree, prefix=""):
    # Sort directories first, then files
    entries = sorted(tree.items(), key=lambda x: (x[1] is None, x[0]))
    lines = []
    for i, (name, subtree) in enumerate(entries):
        connector = "├── " if i < len(entries) - 1 else "└── "
        if subtree is None:
            lines.append(prefix + connector + name)
        else:
            lines.append(prefix + connector + name)
            new_prefix = prefix + ("│   " if i < len(entries) - 1 else "    ")
            lines.extend(format_directory_tree(subtree, new_prefix))
    return lines

def write_directory_tree(out, included_files):
    tree_structure = build_directory_tree_structure(included_files)
    out.write("Project Directory Structure:\n\n")
    out.write("```\n")
    out.write(".\n")
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
        write_directory_tree(out, included_files)

        for fpath in included_files:
            out.write(f"## File: {fpath}\n")
            full_path = os.path.join(input_dir, fpath)
            with open(full_path, "r", encoding='utf-8', errors='replace') as f:
                out.write(f.read())
                out.write("\n")

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

        with open(zip_path, "rb") as f:
            zip_data = f.read()
            encoded = base64.b64encode(zip_data).decode('utf-8')

    with open(output_file, "w") as out:
        write_directory_tree(out, included_files)
        out.write(encoded)

        instructions = dedent('''
        ---------------------------
        Instructions for the Assistant
        ---------------------------
        The text above is a base64-encoded ZIP containing the filtered project files.

        To use it in this chat environment:
        1. Consider the above text as the encoded form of the code.
        2. "Decode" it mentally and imagine the files have been restored from the ZIP.
        3. If --language=node, you'll see:
           - 'package.json' if it exists in the project root
           - All matching files (e.g. .js, .mjs, .jsx) under src/
        4. If --language=none + --extension-list "json", you'll see .json files from anywhere, skipping package.json.
        ''')
        out.write(instructions)

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) < 2:
        print("Usage: python bundler.py <input_directory> <output_text_file> [--no-encode] [--extension-list EXT_LIST] [--language LANG]")
        sys.exit(1)

    input_directory = args[0]
    output_text_file = args[1]

    no_encode = False
    user_extensions = None
    language = 'node'  # default

    i = 2
    while i < len(args):
        if args[i] == "--no-encode":
            no_encode = True
        elif args[i] == "--extension-list":
            if i + 1 >= len(args):
                print("Error: --extension-list requires a comma-separated list argument (e.g. 'js,mjs,jsx' or 'json').")
                sys.exit(1)
            user_extensions = [ext.strip().lower() for ext in args[i+1].split(",")]
            i += 1
        elif args[i] == "--language":
            if i + 1 >= len(args):
                print("Error: --language requires an argument (e.g. 'node' or 'none').")
                sys.exit(1)
            language = args[i+1].strip().lower()
            i += 1
        i += 1

    if not os.path.isdir(input_directory):
        print(f"Error: {input_directory} is not a directory.")
        sys.exit(1)

    included_files = get_included_files(input_directory, user_extensions, language)

    if no_encode:
        write_direct_listings(input_directory, output_text_file, included_files)
        print(f"Included files have been listed directly in {output_text_file}.")
    else:
        write_encoded_listing(input_directory, output_text_file, included_files)
        print(f"Filtered files have been bundled + base64-encoded in {output_text_file}.")
        print("Copy/paste it into the chat environment and follow instructions at the bottom of that file.")
