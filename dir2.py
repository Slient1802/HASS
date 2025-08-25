import os
import fnmatch

def _is_ignored(path, ignore_patterns):
    """
    Checks if a given path should be ignored based on .gitignore patterns.
    
    Args:
        path (str): The path to check, relative to the project root.
        ignore_patterns (list): A list of .gitignore patterns.
        
    Returns:
        bool: True if the path should be ignored, False otherwise.
    """
    # Normalize the path for consistent matching
    path = os.path.normpath(path)

    for pattern in ignore_patterns:
        # A pattern ending with a slash only matches a directory
        is_directory_pattern = pattern.endswith('/')
        pattern_to_match = pattern.rstrip('/')

        # Handle directory-specific patterns
        if is_directory_pattern:
            # Match the full relative path if it's a directory
            if os.path.isdir(os.path.join('.', path)) and fnmatch.fnmatch(path, pattern_to_match):
                return True
            # Also handle patterns for subdirectories (e.g., 'build/' matches 'src/build/')
            if fnmatch.fnmatch(path, f"*/{pattern_to_match}"):
                return True
        else:
            # Handle patterns that match the full relative path
            if fnmatch.fnmatch(path, pattern):
                return True
            # Handle patterns that only match the filename (e.g., '*.log')
            if fnmatch.fnmatch(os.path.basename(path), pattern):
                return True
            
    return False

def generate_file_tree(project_path='.'):
    """
    Generates a list of files and directories in a tree-like format,
    respecting .gitignore rules.
    
    Args:
        project_path (str): The path to the project directory.
        
    Returns:
        str: The formatted file tree content as a single string.
    """
    project_path = os.path.abspath(project_path)
    file_list = []
    
    # Read .gitignore patterns
    ignore_patterns = []
    gitignore_path = os.path.join(project_path, '.gitignore')
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Strip leading slash as fnmatch works better on relative paths
                    ignore_patterns.append(line.lstrip('/'))

    for root, dirs, files in os.walk(project_path):
        relative_root = os.path.relpath(root, project_path)

        # Crucial step: Explicitly remove the .git directory and others from the start
        # of the list to prevent walking into them.
        dirs_to_remove = ['.git']
        dirs_to_remove.extend([d for d in dirs if _is_ignored(os.path.join(relative_root, d), ignore_patterns)])
        
        for d in dirs_to_remove:
            if d in dirs:
                dirs.remove(d)

        # Add the current directory to the list if it's not the root and is not ignored
        if relative_root != '.' and not _is_ignored(relative_root, ignore_patterns):
            file_list.append(relative_root.replace('\\', '/') + '/')
        
        # Add non-ignored files
        for file in files:
            file_path_relative_to_project = os.path.join(relative_root, file)
            if not _is_ignored(file_path_relative_to_project, ignore_patterns):
                # Format the path for the output
                if relative_root == '.':
                    file_list.append(file)
                else:
                    file_list.append(os.path.join(relative_root, file).replace('\\', '/'))
                    
    # Ensure directories are correctly added to the list, even if they contain no files
    final_paths = set()
    for path in file_list:
        final_paths.add(path)
        parts = path.split('/')
        if len(parts) > 1:
            for i in range(1, len(parts)):
                parent_dir = '/'.join(parts[:i]) + '/'
                final_paths.add(parent_dir)

    # Sort the unique paths for a clean, consistent output
    sorted_paths = sorted(list(final_paths))

    return "\n".join(sorted_paths)

def list_project_files(project_path='.'):
    """
    Main function to generate the file list and save it to a file.
    """
    output_filename = "dir.txt"
    file_tree_content = generate_file_tree(project_path)

    print(f"--- Generating file list for: {os.path.abspath(project_path)} ---")
    
    try:
        with open(output_filename, 'w') as f:
            f.write(file_tree_content)
        print(f"--- File list successfully saved to {output_filename} ---")
    except IOError as e:
        print(f"Error: Unable to write to file {output_filename}. {e}")
    
    print("\n--- Content of dir.txt ---")
    print(file_tree_content)

if __name__ == "__main__":
    list_project_files()