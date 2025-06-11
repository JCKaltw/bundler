# /Users/chris/projects/es2/src/app-bundler.py
#
# Below is the complete listing of app-bundler.py with enhancements:
# 1. Previously added `--root-files` to specify additional root-level files
# 2. Previously added `--include-patterns` to specify glob patterns for including
#    files from alternate directories (e.g., public/*.html, docs/**/*.md)
# 3. FIXED: Modified get_included_files() to prioritize --file-subset files
#    Now files in the subset are ALWAYS included regardless of normal filtering rules
#
# CHANGE EXPLANATION (compared to your last version):
#   1. Fixed the logic in get_included_files() so that files specified in 
#      --file-subset are ALWAYS included, even if they don't match the normal
#      src/app directory or extension filtering rules.
#   2. The fix ensures that files like scripts/bullWorker.js will be included
#      when specified in the file subset, regardless of their location.
#   3. All original comments and functionality remain intact.
#
# IMPORTANT:
#   - We have retained all original functionality (package.json, filters for
#     src/app directories, --root-files, --include-patterns, etc.).
#   - The key fix is in get_included_files() where we now check file_subset
#     FIRST, and if a file is in the subset, we include it regardless of
#     other filtering rules.
#   - No code or comments have been removed (except the problematic logic).
#   - The main block remains at the end.

import os
import sys
import base64
import zipfile
import tempfile
import fnmatch
from textwrap import dedent

def should_include_file(file_path, input_dir, user_extensions=None, language='node', root_files=None, include_patterns=None):
    """
    Decide if file_path should be included based on:
      1. Exclusions: node_modules, .next, package-lock.json
      2. If language='node' (default):
           - Include ONLY 'package.json' at the root (if present),
             OR any file that appears in root_files (new feature),
             but only if it's actually at the root (i.e. no subdirs).
           - Include any file within 'src/' or 'app/' (recursively) that matches
             the extension list (defaulting to ['js','mjs','jsx','ts','tsx','css'] if none provided).
      3. If language='none':
           - Ignore 'package.json' root file.
           - Include any file (from any path) that matches the extension list (if provided),
             e.g. .json files. If none provided, likely includes nothing.
      4. NEW: Include any file that matches patterns specified in include_patterns
           (e.g., public/*.html, docs/**/*.md) - this works for any language mode.
    """
    if root_files is None:
        root_files = []
    if include_patterns is None:
        include_patterns = []

    rel_path = os.path.relpath(file_path, start=input_dir)
    path_parts = rel_path.split(os.sep)

    # -- 1. Exclusion rules
    if 'node_modules' in path_parts:
        return False
    if '.next' in path_parts:
        return False
    if rel_path == 'package-lock.json':
        return False

    # -- NEW: Check include patterns first (applies to all language modes)
    for pattern in include_patterns:
        if fnmatch.fnmatch(rel_path, pattern):
            return True

    # -- 2. If language='node'
    if language == 'node':
        # By default, if user hasn't provided an --extension-list, we use these
        if not user_extensions:
            user_extensions = ['js','mjs','jsx','ts','tsx','css']
        # Normalize them
        user_extensions = [ext.lower() for ext in user_extensions]

        # If exactly 'package.json' at the root
        if rel_path == 'package.json':
            return True

        # NEW FEATURE: if the file is at the root and listed in root_files
        if len(path_parts) == 1 and rel_path in root_files:
            return True

        # Otherwise, include files under 'src/' or 'app/'
        if (rel_path.startswith('src' + os.sep) or rel_path.startswith('app' + os.sep)):
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

    # If some other language is passed, we mimic 'node' logic as a fallback.
    else:
        if not user_extensions:
            user_extensions = ['js','mjs','jsx','ts','tsx','css']
        user_extensions = [ext.lower() for ext in user_extensions]

        # If exactly 'package.json' at the root
        if rel_path == 'package.json':
            return True
        
        # If the file is at the root and is in root_files
        if len(path_parts) == 1 and rel_path in root_files:
            return True

        # Otherwise, only files under 'src/' or 'app/' that match the extension list
        if (rel_path.startswith('src' + os.sep) or rel_path.startswith('app' + os.sep)):
            _, ext = os.path.splitext(rel_path)
            ext = ext.lower().lstrip('.')  # e.g. "js"
            return ext in user_extensions

        return False

def get_included_files(input_dir, user_extensions=None, language='node', file_subset=None, root_files=None, include_patterns=None):
    """
    Walk through input_dir and return a sorted list of files that meet the
    should_include_file(...) criteria. If file_subset (list) is provided,
    ALL files in that subset will be included regardless of normal filtering rules.
    """
    included_files = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            filepath = os.path.join(root, file)
            rel_path = os.path.relpath(filepath, start=input_dir)
            
            # FIXED LOGIC: If file_subset is provided, check it FIRST
            # Files in the subset are ALWAYS included regardless of normal filtering
            if file_subset is not None:
                if rel_path in file_subset:
                    included_files.append(rel_path)
                    continue
                # If file_subset is provided but this file is not in it, skip it
                continue
            
            # If no file_subset, apply normal filtering rules
            if should_include_file(filepath, input_dir, user_extensions, language, root_files, include_patterns):
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
        # Final part is the file name
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

def write_directory_tree(out, included_files, root_dir):
    """
    Writes a tree structure to 'out', including the actual root directory name
    (instead of just '.').
    """
    tree_structure = build_directory_tree_structure(included_files)
    out.write("Project Directory Structure:\n\n")
    out.write("```\n")
    # Use the base name of the provided directory instead of '.'
    root_name = os.path.basename(os.path.normpath(root_dir))
    if not root_name:
        root_name = '.'
    out.write(root_name + "\n")
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
    """
    Writes the directory tree and the actual contents of each included file.
    Also includes the full disk path for clarity.
    """
    with open(output_file, "a") as out:  # 'a' to append if multiple dirs
        write_directory_tree(out, included_files, input_dir)

        for fpath in included_files:
            out.write(f"## File: {fpath}\n")
            # Provide the absolute path as a comment
            out.write(f"# Full path under root '{os.path.abspath(input_dir)}' is: {os.path.join(os.path.abspath(input_dir), fpath)}\n\n")
            full_path = os.path.join(input_dir, fpath)
            with open(full_path, "r", encoding='utf-8', errors='replace') as f:
                out.write(f.read())
                out.write("\n")

def write_direct_listings_tree_only(input_dir, output_file, included_files):
    """
    Writes only the directory tree for the given root,
    omitting file contents (tree-only mode).
    """
    with open(output_file, "a") as out:
        write_directory_tree(out, included_files, input_dir)

def write_direct_listings_instructions(output_file):
    """
    Appends the usage instructions for direct listings, if needed.
    We only append them once at the end, for all processed roots.
    """
    instructions = dedent('''
    ---------------------------
    Instructions for the Assistant
    ---------------------------
    The text above includes the full plaintext listings of each included source file (if not tree-only).
    Consider each "## File: filename" line as a boundary between files.

    To use this in the chat environment:
    1. Imagine these files are restored into a directory structure according to their paths.
    2. Review and potentially improve the code. Ask any follow-up questions if needed.
    ''')
    with open(output_file, "a") as out:
        out.write(instructions)
        out.write("\n")

def write_encoded_listing(input_dir, output_file, included_files):
    """
    Writes the directory tree plus a base64-encoded ZIP of included files.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "filtered_app.zip")
        zip_filtered_directory(input_dir, zip_path, included_files)

        with open(zip_path, "rb") as f:
            zip_data = f.read()
            encoded = base64.b64encode(zip_data).decode('utf-8')

    with open(output_file, "a") as out:
        write_directory_tree(out, included_files, input_dir)
        out.write(encoded)
        out.write("\n")

def write_encoded_listing_tree_only(input_dir, output_file, included_files):
    """
    In encoded mode, if a root is tree-only, we do NOT add file contents to the ZIP,
    effectively giving only the directory tree. (We still show the tree for clarity.)
    """
    with open(output_file, "a") as out:
        write_directory_tree(out, included_files, input_dir)

def write_encoded_instructions(output_file):
    """
    Appends the usage instructions for the base64-encoded approach, if needed.
    We only append them once at the end, for all processed roots.
    """
    instructions = dedent('''
    ---------------------------
    Instructions for the Assistant
    ---------------------------
    The text above is a base64-encoded ZIP (for roots not marked as tree-only) containing the filtered project files.
    Roots marked as tree-only only display the directory tree without file contents.

    To use it in this chat environment:
    1. Consider the above text as the encoded form of the code (only for non-tree-only directories).
    2. "Decode" it mentally and imagine the files have been restored from the ZIP.
    3. If --language=node, you'll see:
       - 'package.json' if it exists in the project root
       - All matching files (e.g. .js, .mjs, .jsx, .ts, .tsx, .css) under src/ or app/
       - Additional root-level files specified by --root-files (new feature).
       - Files matching patterns specified by --include-patterns (new feature).
    4. If --language=none + --extension-list="json", you'll see .json files from the entire project (excluding package.json).
    5. Files matching --include-patterns will be included regardless of language mode.
    6. If --file-subset is used, ALL files in the subset will be included regardless of other filtering rules.
    ''')
    with open(output_file, "a") as out:
        out.write(instructions)
        out.write("\n")

def parse_options(arglist, start_index):
    """
    Parse global options (before we parse directories in multi-mode).
    Returns:
        - next_index (int): position where we stop parsing
        - no_encode (bool)
        - user_extensions (list or None)
        - language (str)
        - file_subset (list or None)
        - root_files (list or None)
        - include_patterns (list or None)  <-- new addition
    """
    ne = False
    ue = None
    lang = 'node'
    file_subset = None  # new variable
    root_files = []     # new variable for additional root-level files
    include_patterns = []  # new variable for glob patterns
    i = start_index
    while i < len(arglist):
        item = arglist[i]
        if item == "--no-encode":
            ne = True
            i += 1
        elif item == "--extension-list":
            # e.g. --extension-list js,mjs,jsx
            if i + 1 >= len(arglist):
                print("Error: --extension-list requires a comma-separated list argument (e.g. 'js,mjs,jsx' or 'json').")
                sys.exit(1)
            ue = [ext.strip().lower() for ext in arglist[i+1].split(",")]
            i += 2
        elif item.startswith("--extension-list="):
            # e.g. --extension-list=js,mjs,jsx
            val = item.split("=", 1)[1]
            ue = [ext.strip().lower() for ext in val.split(",")]
            i += 1
        elif item == "--language":
            if i + 1 >= len(arglist):
                print("Error: --language requires an argument (e.g. 'node' or 'none').")
                sys.exit(1)
            lang = arglist[i+1].strip().lower()
            i += 2
        elif item.startswith("--language="):
            # e.g. --language=none
            val = item.split("=", 1)[1]
            lang = val.strip().lower()
            i += 1
        elif item == "--file-subset":
            # e.g. --file-subset path/to/file
            if i + 1 >= len(arglist):
                print("Error: --file-subset requires a path to a file.")
                sys.exit(1)
            subset_path = arglist[i+1].strip()
            i += 2
            # Attempt to read lines from subset_path:
            if not os.path.isfile(subset_path):
                print(f"Error: The file-subset path '{subset_path}' is not a valid file.")
                sys.exit(1)
            with open(subset_path, "r", encoding="utf-8") as sf:
                lines = sf.readlines()
            # Strip out newline characters
            file_subset = [ln.rstrip("\n\r") for ln in lines if ln.strip()]
        elif item.startswith("--file-subset="):
            # e.g. --file-subset=path/to/file
            subset_path = item.split("=", 1)[1].strip()
            i += 1
            if not os.path.isfile(subset_path):
                print(f"Error: The file-subset path '{subset_path}' is not a valid file.")
                sys.exit(1)
            with open(subset_path, "r", encoding="utf-8") as sf:
                lines = sf.readlines()
            # Strip out newline characters
            file_subset = [ln.rstrip("\n\r") for ln in lines if ln.strip()]
        elif item == "--root-files":
            # e.g. --root-files next.config.js,foo.js
            if i + 1 >= len(arglist):
                print("Error: --root-files requires a comma-separated list.")
                sys.exit(1)
            root_files = [rf.strip() for rf in arglist[i+1].split(",")]
            i += 2
        elif item.startswith("--root-files="):
            # e.g. --root-files=next.config.js,foo.js
            val = item.split("=", 1)[1]
            root_files = [rf.strip() for rf in val.split(",")]
            i += 1
        elif item == "--include-patterns":
            # e.g. --include-patterns public/*.html,docs/**/*.md
            if i + 1 >= len(arglist):
                print("Error: --include-patterns requires a comma-separated list of glob patterns.")
                sys.exit(1)
            include_patterns = [pattern.strip() for pattern in arglist[i+1].split(",")]
            i += 2
        elif item.startswith("--include-patterns="):
            # e.g. --include-patterns=public/*.html,docs/**/*.md
            val = item.split("=", 1)[1]
            include_patterns = [pattern.strip() for pattern in val.split(",")]
            i += 1
        elif item.startswith("--"):
            # If this is something else, break (it might be directory-specific like --tree-only)
            break
        else:
            # Not an option, so break
            break
    return i, ne, ue, lang, file_subset, root_files, include_patterns

def parse_directories_with_tree_only(arglist, start_index):
    """
    For multi-directory mode, parse each directory plus the optional --tree-only flag
    that may appear immediately after it. This continues until we have no more arguments.
    Returns a list of tuples: [(dir_path, tree_only_bool), ...]
    """
    dirs_info = []
    i = start_index
    while i < len(arglist):
        dir_candidate = arglist[i]
        if dir_candidate.startswith("--"):
            print(f"Error: Expected a directory path but got option '{dir_candidate}' unexpectedly.")
            sys.exit(1)
        dirs_info.append((dir_candidate, False))  # default tree_only=False
        i += 1
        # Check if next token is '--tree-only'
        if i < len(arglist) and arglist[i] == "--tree-only":
            dirs_info[-1] = (dir_candidate, True)
            i += 1
    return dirs_info

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) < 2:
        print("Usage (single directory):")
        print("   python bundler.py <input_directory> <output_text_file> [--no-encode] [--extension-list EXT_LIST] [--language LANG] [--tree-only] [--file-subset path_to_file] [--root-files rootfile1,rootfile2] [--include-patterns pattern1,pattern2]")
        print("Usage (multiple directories):")
        print("   python bundler.py <output_text_file> [--no-encode] [--extension-list EXT_LIST] [--language LANG] [--file-subset path_to_file] [--root-files rootfile1,rootfile2] [--include-patterns pattern1,pattern2]")
        print("       <dir1> [--tree-only] <dir2> [--tree-only] ...")
        sys.exit(1)

    might_be_multi_mode = False
    if args[1].startswith("--"):
        might_be_multi_mode = True
    else:
        for a in args[2:]:
            if a.startswith("--"):
                break
            might_be_multi_mode = True
            break

    no_encode = False
    user_extensions = None
    language = 'node'
    file_subset = None
    root_files = []
    include_patterns = []

    if might_be_multi_mode:
        # Multi-directory approach
        output_text_file = args[0]
        idx, no_encode, user_extensions, language, file_subset, root_files, include_patterns = parse_options(args, 1)
        dirs_info = parse_directories_with_tree_only(args, idx)
        if not dirs_info:
            print("Error: no input directories specified in multi-directory mode.")
            sys.exit(1)

        # Overwrite the output file from scratch:
        with open(output_text_file, "w"):
            pass

        saw_non_tree = False

        if no_encode:
            for (d, tree_only) in dirs_info:
                if not os.path.isdir(d):
                    print(f"Error: {d} is not a directory.")
                    sys.exit(1)
                included_files = get_included_files(d, user_extensions, language, file_subset, root_files, include_patterns)
                if tree_only:
                    write_direct_listings_tree_only(d, output_text_file, included_files)
                else:
                    saw_non_tree = True
                    write_direct_listings(d, output_text_file, included_files)
            if saw_non_tree:
                write_direct_listings_instructions(output_text_file)
            print(f"Included files have been listed (or tree-only) in {output_text_file}.")

        else:
            for (d, tree_only) in dirs_info:
                if not os.path.isdir(d):
                    print(f"Error: {d} is not a directory.")
                    sys.exit(1)
                included_files = get_included_files(d, user_extensions, language, file_subset, root_files, include_patterns)
                if tree_only:
                    write_encoded_listing_tree_only(d, output_text_file, included_files)
                else:
                    saw_non_tree = True
                    write_encoded_listing(d, output_text_file, included_files)
            if saw_non_tree:
                write_encoded_instructions(output_text_file)
            print(f"Filtered files have been bundled or listed as tree-only in {output_text_file}.")
            print("Copy/paste it into the chat environment and follow instructions at the bottom of that file.")

    else:
        # Single-directory usage
        input_directory = args[0]
        output_text_file = args[1]
        opt_index, no_encode, user_extensions, language, file_subset, root_files, include_patterns = parse_options(args, 2)
        tree_only = False
        if opt_index < len(args) and args[opt_index] == "--tree-only":
            tree_only = True
            opt_index += 1

        if not os.path.isdir(input_directory):
            print(f"Error: {input_directory} is not a directory.")
            sys.exit(1)

        included_files = get_included_files(input_directory, user_extensions, language, file_subset, root_files, include_patterns)

        # Overwrite the output file from scratch:
        with open(output_text_file, "w"):
            pass

        if no_encode:
            if tree_only:
                write_direct_listings_tree_only(input_directory, output_text_file, included_files)
                print(f"Tree-only listing for {input_directory} has been written to {output_text_file}.")
            else:
                write_direct_listings(input_directory, output_text_file, included_files)
                write_direct_listings_instructions(output_text_file)
                print(f"Included files have been listed directly in {output_text_file}.")
        else:
            if tree_only:
                write_encoded_listing_tree_only(input_directory, output_text_file, included_files)
                print(f"Tree-only listing (no file contents) for {input_directory} has been written to {output_text_file}.")
            else:
                write_encoded_listing(input_directory, output_text_file, included_files)
                write_encoded_instructions(output_text_file)
                print(f"Filtered files have been bundled + base64-encoded in {output_text_file}.")
                print("Copy/paste it into the chat environment and follow instructions at the bottom of that file.")
