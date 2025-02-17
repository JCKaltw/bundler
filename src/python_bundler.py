#!/usr/bin/env python3
# src/python_bundler.py

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
    included_files = included_files.union(
        find_init_files_for_packages(included_files, project_root)
    )
    
    return included_files

def extract_local_imports(py_file, project_root):
    """
    Parse the Python file's AST to find local imports. 
    We only include files that exist within project_root.
    """
    local_deps = set()
    with open(py_file, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=py_file)

    current_dir = os.path.dirname(py_file)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                dep_file = guess_local_module_path(alias.name, project_root)
                if dep_file:
                    local_deps.add(dep_file)
        elif isinstance(node, ast.ImportFrom):
            # node.module might be None for "from . import foo"
            if node.module is not None:
                dep_file = guess_local_module_path(node.module, project_root)
                if dep_file:
                    local_deps.add(dep_file)
            else:
                # Relative import from the current directory
                for alias in node.names:
                    dep_file = guess_local_module_path(alias.name, current_dir, is_relative=True)
                    if dep_file and dep_file.startswith(os.path.abspath(project_root)):
                        local_deps.add(dep_file)
    return local_deps

def guess_local_module_path(module_name, base_path, is_relative=False):
    """
    Convert a module name like 'utils' or 'mypkg.helpers' to a .py path,
    checking if that file actually exists on disk.
    """
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
    If a directory is a Python package, ensure its __init__.py is included.
    We do this for any ancestor dirs of included .py files.
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

def find_all_py_files(base_dir):
    """
    Recursively find ALL Python files (ending in *.py) in the specified base_dir.
    """
    included_files = set()
    for root, dirs, files in os.walk(base_dir):
        for filename in files:
            if filename.endswith(".py"):
                full_path = os.path.join(root, filename)
                included_files.add(os.path.abspath(full_path))
    return included_files

def zip_files(file_paths, zip_path, base_dir):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for f in file_paths:
            arcname = os.path.relpath(f, start=base_dir)
            zipf.write(f, arcname)

def build_directory_tree(file_paths, project_root):
    """
    Build a directory tree representation as text, explicitly showing
    the name of the root directory (e.g. ./schemas instead of just '.').
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
                lines.append(prefix + connector + entry)
                extension = "    " if i == len(entries) - 1 else "│   "
                lines.extend(format_tree(d[entry], prefix + extension))
            else:
                lines.append(prefix + connector + entry)
        return lines

    # Use the basename of the project_root to label the directory tree
    root_label = os.path.basename(os.path.normpath(project_root))
    # If the basename is empty (unlikely but can happen if project_root is '/'), default to '.'
    if not root_label:
        root_label = '.'
    else:
        # Prepend "./" to match the style of your example
        root_label = f"./{root_label}"

    lines = [root_label]
    lines.extend(format_tree(tree))
    return "\n".join(lines)

def build_multi_root_listing(roots_files):
    """
    Build a textual listing showing, for each root:
      - A full directory tree if it is the first root
      - Only newly included modules for subsequent roots, plus a mention of repeated modules
        referencing the root in which they were first listed

    roots_files: a list of tuples [ (root_path, set_of_included_files, project_root), ... ]

    Returns: A string containing the multi-root usage details (one large text).
    """
    # Track the files that have already been listed, and where they were first listed
    file_origin = {}
    output_lines = []

    for idx, (root_path, files_set, project_root) in enumerate(roots_files):
        # Sort by directory structure to keep things consistent
        if idx == 0:
            # First root: show full directory tree
            tree_text = build_directory_tree(files_set, project_root)
            output_lines.append(f"Root #{idx+1}: {root_path} (Full listing)\n{tree_text}\n")
            # Mark origin
            for f in files_set:
                file_origin[f] = root_path
        else:
            # Subsequent root
            new_files = []
            repeated_files = []
            for f in files_set:
                if f not in file_origin:
                    new_files.append(f)
                    file_origin[f] = root_path
                else:
                    repeated_files.append(f)

            new_files = set(new_files)
            repeated_files = set(repeated_files)

            # Build tree for newly introduced files
            if new_files:
                tree_text = build_directory_tree(new_files, project_root)
                output_lines.append(
                    f"Root #{idx+1}: {root_path}\n"
                    f"New modules introduced:\n{tree_text}\n"
                )
            else:
                output_lines.append(
                    f"Root #{idx+1}: {root_path}\nNo new modules introduced.\n"
                )

            # Mention repeated files
            if repeated_files:
                output_lines.append("Previously listed modules for this root:\n")
                for rf in sorted(repeated_files):
                    rel_path = os.path.relpath(rf, start=project_root)
                    original_root = file_origin[rf]
                    output_lines.append(
                        f"  {rel_path} (already listed under root: {original_root})"
                    )
                output_lines.append("")  # extra line break

    return "\n".join(output_lines)

if __name__ == "__main__":
    # Usage: 
    #   python3 python_bundler.py [--no-encode] <source_path> <output_text_file>
    #
    # or (multi-root mode):
    #   python3 python_bundler.py [--no-encode] <source_path_1> [<source_path_2> ... <source_path_n>] <output_text_file>
    #
    # where each <source_path_i> can be either:
    #   - a Python file: we parse imports to find local deps
    #   - a directory: we collect *all* .py files in that directory

    if len(sys.argv) < 3:
        print("Usage: python3 python_bundler.py [--no-encode] <source_path> [<source_path2> ...] <output_text_file>")
        sys.exit(1)

    args = sys.argv[1:]
    no_encode = False

    # Check for --no-encode
    if "--no-encode" in args:
        no_encode = True
        args.remove("--no-encode")

    # After removing --no-encode, we need at least 2 arguments:
    #   single-root mode: <source_path> <output_text_file>
    #   multi-root mode:  <source_path_1> <source_path_2> ... <source_path_n> <output_text_file>
    if len(args) < 2:
        print("Usage: python3 python_bundler.py [--no-encode] <source_path> [<source_path2> ...] <output_text_file>")
        sys.exit(1)

    # The last argument is always the output text file
    output_text_file = args[-1]
    source_paths = args[:-1]

    # If only one source path, run single-root logic exactly as before
    if len(source_paths) == 1:
        source_path = source_paths[0]
        if not (os.path.isdir(source_path) or os.path.isfile(source_path)):
            print(f"Error: {source_path} is neither a valid file nor a directory.")
            sys.exit(1)

        # Single-root gather
        if os.path.isdir(source_path):
            project_root = os.path.abspath(source_path)
            included_files = find_all_py_files(project_root)
        else:
            project_root = os.path.dirname(os.path.abspath(source_path))
            included_files = find_local_dependencies(source_path, project_root)

        # Build directory tree for the single root
        directory_tree = build_directory_tree(included_files, project_root)

        # Decide output mode
        if no_encode:
            # ----------------------------------------------------
            # --no-encode mode: plain text listings, no instructions
            # ----------------------------------------------------
            with open(output_text_file, "w", encoding="utf-8") as out:
                # Write the directory tree at the top
                out.write(directory_tree)
                out.write("\n\n")

                # For each included file, write a header and its contents
                for fpath in sorted(included_files):
                    rel_path = os.path.relpath(fpath, start=project_root)
                    out.write(f"--- BEGIN FILE: {rel_path} ---\n")
                    with open(fpath, "r", encoding="utf-8") as fin:
                        out.write(fin.read())
                    out.write(f"\n--- END FILE: {rel_path} ---\n\n")

            print(f"All included files have been written as plain text to {output_text_file}.")
        else:
            # ----------------------------------------------------
            # Original behavior: ZIP + Base64 + instructions
            # ----------------------------------------------------
            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = os.path.join(tmpdir, "filtered_app.zip")
                zip_files(included_files, zip_path, project_root)

                with open(zip_path, "rb") as f:
                    zip_data = f.read()
                    encoded = base64.b64encode(zip_data).decode('utf-8')

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

            with open(output_text_file, "w", encoding="utf-8") as out:
                out.write(encoded)
                out.write(instructions)

            print(f"Filtered files have been successfully bundled and saved to {output_text_file}.")
            print("Only the locally coded files have been included in the output.")
            print("Copy the entire contents of that file and paste it into the chat environment.")
            print("Follow the instructions at the bottom of the file to interpret and improve the code.")

    else:
        # ----------------------------------------------------
        # Multi-root mode
        # ----------------------------------------------------
        # We gather dependencies for each source path, then unify them.
        # We also build a special listing that shows repeated modules only once.
        roots_files = []
        all_included_files = set()

        # We will use the first root's directory as the principal "project_root" for final zipping,
        # but each root's actual directory is used for scanning its own dependencies.
        first_path = source_paths[0]
        if os.path.isfile(first_path):
            main_project_root = os.path.dirname(os.path.abspath(first_path))
        else:
            main_project_root = os.path.abspath(first_path)

        for spath in source_paths:
            if not (os.path.isdir(spath) or os.path.isfile(spath)):
                print(f"Error: {spath} is neither a valid file nor a directory.")
                sys.exit(1)

            if os.path.isdir(spath):
                this_project_root = os.path.abspath(spath)
                these_files = find_all_py_files(this_project_root)
            else:
                this_project_root = os.path.dirname(os.path.abspath(spath))
                these_files = find_local_dependencies(spath, this_project_root)

            roots_files.append((spath, these_files, this_project_root))
            all_included_files.update(these_files)

        # Build the multi-root textual listing
        multi_root_listing = build_multi_root_listing(roots_files)

        # Decide how to output
        if no_encode:
            # ----------------------------------------------------
            # --no-encode mode: plain text listings, no instructions
            #   In multi-root mode, we still combine all included files,
            #   but we show a multi-root breakdown as requested.
            # ----------------------------------------------------
            with open(output_text_file, "w", encoding="utf-8") as out:
                out.write("==== Multi-Root Module Listing ====\n")
                out.write(multi_root_listing)
                out.write("\n\n")

                # For each included file (unique), write a header and its contents
                # We'll sort them to have consistent order
                for fpath in sorted(all_included_files):
                    rel_path = os.path.relpath(fpath, start=main_project_root)
                    out.write(f"--- BEGIN FILE: {rel_path} ---\n")
                    with open(fpath, "r", encoding="utf-8") as fin:
                        out.write(fin.read())
                    out.write(f"\n--- END FILE: {rel_path} ---\n\n")

            print(f"All included files (from multiple roots) have been written as plain text to {output_text_file}.")
        else:
            # ----------------------------------------------------
            # ZIP + Base64 + instructions
            # ----------------------------------------------------
            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = os.path.join(tmpdir, "filtered_app.zip")
                zip_files(all_included_files, zip_path, main_project_root)

                with open(zip_path, "rb") as f:
                    zip_data = f.read()
                    encoded = base64.b64encode(zip_data).decode('utf-8')

            instructions = dedent('''
            ---------------------------
            Instructions for the Assistant
            ---------------------------
            The text above is a base64-encoded ZIP containing a Python project’s filtered source code from multiple roots.
            Only locally coded files are included. External libraries or unresolvable imports were excluded.
            To use it in this chat environment:
            1. Consider the above text as the encoded form of the application’s source code.
            2. "Decode" it mentally and imagine the files have been restored from the ZIP.
            3. Below is the directory breakdown (for multiple roots) of the included files for reference:

            ''') + multi_root_listing + dedent('''

            4. Once "decoded," please summarize the structure and content of these files.
            5. Then, provide coding enhancements, improvements, or suggestions based on the given source.
            6. Feel free to ask for clarification on any file or code segment.
            ''')

            with open(output_text_file, "w", encoding="utf-8") as out:
                out.write(encoded)
                out.write(instructions)

            print(f"Filtered files (from multiple roots) have been successfully bundled and saved to {output_text_file}.")
            print("Only the locally coded files have been included in the output.")
            print("Copy the entire contents of that file and paste it into the chat environment.")
            print("Follow the instructions at the bottom of the file to interpret and improve the code.")
