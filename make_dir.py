# -*- coding: utf-8 -*-
import os

def create_from_file(file_path):
    """
    Creates a directory and file structure based on a text file.
    The script reads each line and checks if it's a file or directory.
    
    Args:
        file_path (str): The path to the text file containing the directory structure.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy tệp '{file_path}'. Vui lòng đảm bảo tệp này có trong thư mục dự án.")
        return

    print("Bắt đầu tạo cấu trúc thư mục...")
    for line in lines:
        # Strip leading and trailing whitespace
        path = line.strip()
        
        # Skip empty lines
        if not path:
            continue
            
        # Check for a specific case like "..." which might appear
        if path == '...':
            continue

        # Check if the path is a file or a directory
        # The logic is simple: if the path has a '.', we treat it as a file.
        # This can be refined based on user needs.
        if '.' in os.path.basename(path):
            # If the path is a file, create its parent directory first
            dir_path = os.path.dirname(path)
            if dir_path and not os.path.exists(dir_path):
                print(f"Tạo thư mục cha: {dir_path}")
                os.makedirs(dir_path, exist_ok=True)
            
            # Create the empty file
            if not os.path.exists(path):
                print(f"Tạo tệp: {path}")
                with open(path, 'w') as new_file:
                    pass  # Create an empty file
        else:
            # Handle the path as a directory
            # Create the directory and all its parent directories
            if not os.path.exists(path):
                print(f"Tạo thư mục: {path}")
                os.makedirs(path, exist_ok=True)

    print("Hoàn tất việc tạo cấu trúc thư mục.")

if __name__ == "__main__":
    # The file containing the directory structure
    dir_file = "dir.txt"
    create_from_file(dir_file)
