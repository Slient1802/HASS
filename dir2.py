import os
import fnmatch

def list_project_files(project_path='.'):
    """
    Lists all files within the specified project directory and its subdirectories,
    ignoring files and directories specified in a .gitignore file.

    Args:
        project_path (str): The path to the project directory.
                            Defaults to '.' (the current directory).
    """
    print(f"--- Files in project: {os.path.abspath(project_path)} ---")

    gitignore_path = os.path.join(project_path, '.gitignore')
    ignore_patterns = []

    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Gitignore patterns can be tricky. This aims for common cases.
                    # Handle leading slashes: /foo matches foo only at the root of the repo
                    if line.startswith('/'):
                        # Store as relative path from project_path without leading slash
                        ignore_patterns.append(line[1:])
                    else:
                        ignore_patterns.append(line)
        print(f"--- .gitignore found. Ignoring patterns: {ignore_patterns} ---")
    else:
        print("--- No .gitignore found. All files will be listed. ---")

    for root, dirs, files in os.walk(project_path):
        # Calculate the relative path from the project_path to the current root
        relative_root = os.path.relpath(root, project_path)
        
        # Normalize relative_root for consistent matching (e.g., '.' becomes '')
        if relative_root == '.':
            normalized_relative_root = ''
        else:
            normalized_relative_root = relative_root + os.sep # Add separator for directory matching

        # Always explicitly remove .git directory if it's found
        if '.git' in dirs and os.path.normpath(os.path.join(relative_root, '.git')) == os.path.normpath('.git'):
            dirs.remove('.git')

        # Filter out ignored directories before processing files
        # We iterate over a copy of `dirs` to safely remove items
        dirs_to_remove = []
        for d in dirs:
            # Path for checking against patterns (e.g., "src/build" or "temp_folder")
            full_dir_path_relative_to_project = os.path.normpath(os.path.join(normalized_relative_root, d))
            
            is_ignored = False
            for pattern in ignore_patterns:
                # Handle directory patterns (e.g., build/, /build)
                # Ensure trailing slash for directory patterns when matching
                if pattern.endswith('/'):
                    # Match if the directory path starts with the pattern (for sub-directories)
                    if fnmatch.fnmatch(full_dir_path_relative_to_project + os.sep, pattern):
                        is_ignored = True
                        break
                    # For root-level directory patterns, also check exact match with leading slash
                    elif pattern.startswith('/') and fnmatch.fnmatch(full_dir_path_relative_to_project, pattern[1:]):
                         is_ignored = True
                         break
                # Handle direct folder name matches (e.g., .vscode, my_folder)
                # Check both full path relative to project and just the directory name
                elif fnmatch.fnmatch(full_dir_path_relative_to_project, pattern) or fnmatch.fnmatch(d, pattern):
                    is_ignored = True
                    break

            if is_ignored:
                dirs_to_remove.append(d)

        for d_to_remove in dirs_to_remove:
            if d_to_remove in dirs:
                dirs.remove(d_to_remove)

        # Determine the path to display
        display_path = "Current Directory" if relative_root == '.' else relative_root

        # Check if the current directory itself should be ignored based on patterns
        # This is mainly for the case where `os.walk` yields a directory that matches an ignore pattern
        is_current_dir_ignored = False
        for pattern in ignore_patterns:
            # Match directories with trailing slash (e.g., `build/`)
            if pattern.endswith('/'):
                if fnmatch.fnmatch(normalized_relative_root, pattern): # Check if the current root matches a directory pattern
                    is_current_dir_ignored = True
                    break
            # Match exact directory names (e.g., `my_folder`)
            elif fnmatch.fnmatch(relative_root, pattern):
                is_current_dir_ignored = True
                break
            
        if not is_current_dir_ignored:
            print(f"\nDirectory: {display_path}/")

            # Filter out ignored files
            filtered_files = []
            for file in files:
                full_file_path_relative_to_project = os.path.normpath(os.path.join(normalized_relative_root, file))
                
                is_ignored = False
                for pattern in ignore_patterns:
                    # Handle patterns matching the full relative path (e.g., /config.ini)
                    if fnmatch.fnmatch(full_file_path_relative_to_project, pattern):
                        is_ignored = True
                        break
                    # Handle patterns matching just the filename (e.g., *.log, temp.*)
                    elif fnmatch.fnmatch(file, pattern):
                        is_ignored = True
                        break
                        
                if not is_ignored:
                    filtered_files.append(file)

            if filtered_files:
                for file in filtered_files:
                    print(f"  - {file}")
            else:
                print("  (No files in this directory or all files are ignored)")

if __name__ == "__main__":
    # How to use:
    # 1. Save this code as a Python file (e.g., `list_repo_files.py`).
    # 2. Open your terminal or command prompt.
    # 3. Navigate to the root directory of your local GitHub repository.
    #    Example: cd /Users/yourusername/Documents/GitHub/your-repo-name
    # 4. Run the script: python list_repo_files.py

    # The '.' refers to the current working directory, which should be
    # the root of your local GitHub repository when you run the script there.
    project_directory = "."
    
    list_project_files(project_directory)