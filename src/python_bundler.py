#!/usr/bin/env python3
import os
import sys
import base64
import zipfile
import tempfile
import ast
from textwrap import dedent

def find_local_dependencies(entry_point, project_root):
    """
    Recursively find local Python files imported by the entry point.
    Only includes files that physically exist in the project root directory.
    """
    visited = set()
    to_visit = [os.path.abspath(entry_point)]
    included_files = set()

    while to_visit:
        current_file = to_visit.pop()
        if current_file in visited:
            continue
        visited.add(current_file)

        # Ensure file is inside project_root
        if not current_file.startswith(os.path.abspath(project_root)):
            continue

        included_files.add(current_file)
        new_deps = extract_local_imports(current_file, project_root)
        for dep in new_deps:
            if dep not in visited:
                to_visit.append(dep)

    # Include __init__.py files for packages
    included_files = included_files.union(find_init_files_for_packages(included_files, project_root))
    
    return included_files

def extract_local_imports(py_file, project_root):
    """
    Parse the Python file's AST to find local imports. We do not try to import or find specs.
    We only include the file if it exists within the project_root.
    """
    local_deps = set()
    with open(py_file, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=py_file)

    # We'll need the directory of the current file for relative imports
    current_dir = os.path.dirname(py_file)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                dep_file = guess_local_module_path(alias.name, project_root)
                if dep_file:
                    local_deps.add(dep_file)
        elif isinstance(node, ast.ImportFrom):
            # node.module might be None for something like "from . import foo"
            if node.module is not None:
                dep_file = guess_local_module_path(node.module, project_root)
                if dep_file:
                    local_deps.add(dep_file)
            else:
                # Relative import from the current directory
                # For "from . import something", try something.py in current directory
                for alias in node.names:
                    dep_file = guess_local_module_path(alias.name, current_dir, is_relative=True)
                    if dep_file and dep_file.startswith(os.path.abspath(project_root)):
                        local_deps.add(dep_file)

    return local_deps

def guess_local_module_path(module_name, base_path, is_relative=False):
    """
    Given a module name like 'utils' or 'mypkg.helpers' and a base path,
    guess the corresponding .py file. 
    - For absolute references, the base_path is project_root.
    - For relative references, the base_path is the directory of the current file.

    We do not try to resolve using importlib; we only check the filesystem.
    """
    # Convert module_name to a file path: 'mypkg.utils' -> 'mypkg/utils.py'
    rel_path = module_name.replace('.', os.sep) + '.py'
    if is_relative:
        candidate = os.path.join(base_path, rel_path)
    else:
        candidate = os.path.join(base_path, rel_path)
    
    if os.path.isfile(candidate):
        return os.path.abspath(candidate)

    return None

def find_init_files_for_packages(included_files, project_root):
    """
    Ensure that any directories that form packages (i.e., contain __init__.py)
    are also included if they are ancestors of included modules.
    """
    init_files = set()
    for f in included_files:
        current_dir = os.path.dirname(f)
        while True:
            if os.path.abspath(current_dir) == os.path.abspath(project_root):
                break
            init_file = os.path.join(current_dir, '__init__.py')
            if os.path.isfile(init_file):
                init_files.add(os.path.abspath(init_file))
            parent = os.path.dirname(current_dir)
            if parent == current_dir:
                break
            current_dir = parent

    return init_files

def zip_files(file_paths, zip_path, base_dir):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for f in file_paths:
            arcname = os.path.relpath(f, start=base_dir)
            zipf.write(f, arcname)

def build_directory_tree(file_paths, project_root):
    """
    Build a directory tree representation as text.
    """
    rel_paths = [os.path.relpath(p, start=project_root) for p in file_paths]
    rel_paths = sorted(rel_paths)

    # Build hierarchical dict
    tree = {}
    for p in rel_paths:
        parts = p.split(os.sep)
        d = tree
        for part in parts[:-1]:
            d = d.setdefault(part, {})
        d[parts[-1]] = None

    def format_tree(d, prefix=""):
        lines = []
        entries = sorted(d.keys())
        for i, entry in enumerate(entries):
            connector = "└── " if i == len(entries) - 1 else "├── "
            if isinstance(d[entry], dict):
                # Directory
                lines.append(prefix + connector + entry)
                extension = "    " if i == len(entries) - 1 else "│   "
                lines.extend(format_tree(d[entry], prefix + extension))
            else:
                # File
                lines.append(prefix + connector + entry)
        return lines

    lines = ["."]
    lines.extend(format_tree(tree))
    return "\n".join(lines)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 python_bundler.py <root_python_script> <output_text_file>")
        sys.exit(1)

    root_script = sys.argv[1]
    output_text_file = sys.argv[2]

    if not os.path.isfile(root_script):
        print(f"Error: {root_script} is not a valid file.")
        sys.exit(1)

    project_root = os.path.dirname(root_script)

    # Gather all dependencies - local files only
    included_files = find_local_dependencies(root_script, project_root)

    # Zip and base64 encode them
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "filtered_app.zip")
        zip_files(included_files, zip_path, project_root)

        with open(zip_path, "rb") as f:
            zip_data = f.read()
            encoded = base64.b64encode(zip_data).decode('utf-8')

    # Build directory tree of included files
    directory_tree = build_directory_tree(included_files, project_root)

    instructions = dedent('''
    ---------------------------
    Instructions for the Assistant
    ---------------------------
    The text above is a base64-encoded ZIP containing a Python project’s filtered source code.
    Only locally coded files are included. External libraries or unresolvable imports were excluded.
    To use it in this chat environment:
    1. Consider the above text as the encoded form of the application’s source code.
    2. "Decode" it mentally and imagine the files have been restored from the ZIP.
    3. Below is the directory tree of the included files for reference:
    
    ''') + directory_tree + dedent('''

    4. Once "decoded," please summarize the structure and content of these files.
    5. Then, provide coding enhancements, improvements, or suggestions based on the given source.
    6. Feel free to ask for clarification on any file or code segment.
    ''')

    with open(output_text_file, "w") as out:
        out.write(encoded)
        out.write(instructions)

    print(f"Filtered files have been successfully bundled and saved to {output_text_file}.")
    print("Only the locally coded files have been included in the output.")
    print("Copy the entire contents of that file and paste it into the chat environment.")
    print("Follow the instructions at the bottom of the file to interpret and improve the code.")
