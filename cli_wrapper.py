import os
import shutil
import sys
import subprocess
import filecmp

# Optional: For colored output in the terminal
try:
    from colorama import Fore, Style

    colorama_installed = True
except ImportError:
    colorama_installed = False

common_folder_name = "BYODR_utils"


def compare_common_dirs(dir1, dir2):
    differences = []
    dirs_cmp = filecmp.dircmp(dir1, dir2)
    # Files that differ
    for file_name in dirs_cmp.diff_files:
        differences.append(f"Files differ: {os.path.join(dir1, file_name)} and {os.path.join(dir2, file_name)}")
    # Files only in dir1
    for file_name in dirs_cmp.left_only:
        differences.append(f"File only in original {common_folder_name} folder: {os.path.join(dir1, file_name)}")
    # Files only in dir2
    for file_name in dirs_cmp.right_only:
        differences.append(f"File only in '{dir2}' folder: {os.path.join(dir2, file_name)}")
    # Recursively compare subdirectories
    for sub_dir in dirs_cmp.common_dirs:
        sub_differences = compare_common_dirs(os.path.join(dir1, sub_dir), os.path.join(dir2, sub_dir))
        differences.extend(sub_differences)
    return differences


def compare_common_dirs_main(common_dir, dst_common_dir):
    differences = compare_common_dirs(common_dir, dst_common_dir)
    if differences:
        if colorama_installed:
            print(Fore.RED + f"Error: {common_folder_name} folder already exists in '{os.path.dirname(dst_common_dir)}', and there are differences between the original and the copied folder." + Style.RESET_ALL)
        else:
            print(f"Error: {common_folder_name} folder already exists in '{os.path.dirname(dst_common_dir)}', and there are differences between the original and the copied folder.")
        print("Differences found:")
        for diff in differences:
            print(diff)
        return False  # Do not proceed
    else:
        print(f"Warning: {common_folder_name} folder already exists in '{os.path.dirname(dst_common_dir)}', but the files are the same. Proceeding.")
        return True  # Proceed


def compare_and_handle_on_exit(common_dir, dst_common_dir):
    differences = compare_common_dirs(common_dir, dst_common_dir)
    if differences:
        # Differences found; do not delete the copied 'common' folder
        if colorama_installed:
            print(Fore.RED + f"Warning: Changes were made to the {common_folder_name} folder in '{os.path.dirname(dst_common_dir)}'. It will not be deleted." + Style.RESET_ALL)
        else:
            print(f"Warning: Changes were made to the {common_folder_name} folder in '{os.path.dirname(dst_common_dir)}'. It will not be deleted.")
        print("Differences found:")
        for diff in differences:
            print(diff)
    else:
        # No differences; safe to delete the copied 'common' folder
        if os.path.exists(dst_common_dir):
            shutil.rmtree(dst_common_dir)
            print(f"Removed {common_folder_name} folder from '{os.path.basename(dst_common_dir)}'.")
        else:
            print(f"No {common_folder_name} folder to remove from '{os.path.basename(dst_common_dir)}'.")


def main():
    # Check if at least two arguments are provided (script name, target directory)
    if len(sys.argv) < 2:
        print("Usage: python cli_wrapper.py <target_directory> [balena_command] [balena_args]")
        sys.exit(1)

    # Get the target directory from the first argument
    target_dir_name = sys.argv[1]
    target_dir = os.path.join(os.getcwd(), target_dir_name)
    # Ensure the target directory exists
    if not os.path.isdir(target_dir):
        print(f"Error: Target directory '{target_dir_name}' does not exist.")
        sys.exit(1)

    # Define paths
    common_dir = os.path.join(os.getcwd(), common_folder_name)
    dst_common_dir = os.path.join(target_dir, common_folder_name)

    # Extract the Balena CLI command and arguments
    balena_command_args = sys.argv[2:]
    if not balena_command_args:
        print("Error: No Balena CLI command provided.")
        print("Usage: python cli_wrapper.py <target_directory> [balena_command] [balena_args]")
        sys.exit(1)

    # Step 1: Check if 'common' directory exists in target directory
    if os.path.exists(dst_common_dir):
        proceed = compare_common_dirs_main(common_dir, dst_common_dir)
        if not proceed:
            # Exit the script due to differences
            sys.exit(1)
    else:
        # No existing 'common_folder_name' folder in the target directory
        pass

    try:
        # Step 2: Copy the 'common_folder_name' directory into the target directory
        # Remove the existing 'common' folder in target directory if it exists
        if os.path.exists(dst_common_dir):
            shutil.rmtree(dst_common_dir)
        # Copy the 'common' folder
        shutil.copytree(common_dir, dst_common_dir)

        # Step 3: Run the Balena CLI command
        # Build the Balena CLI command
        balena_command = ["balena"] + balena_command_args

        # Set the working directory to the target directory
        subprocess.run(balena_command, cwd=target_dir)
    except KeyboardInterrupt:
        # Handle graceful shutdown (Ctrl+C)
        print("\nScript interrupted by user.")
    finally:
        # Compare and handle the 'common' folder upon exit
        compare_and_handle_on_exit(common_dir, dst_common_dir)


if __name__ == "__main__":
    main()
