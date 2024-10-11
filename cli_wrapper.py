import os
import shutil
import sys
import subprocess
import filecmp


class CLIWrapper:
    def __init__(self, common_folder_name, target_dir_name, balena_command_args):
        """
        Initialize the CLIWrapper with the target directory and Balena command arguments.

        Args:
            target_dir_name (str): Name of the target directory.
            balena_command_args (list): List of arguments for the Balena CLI command.
        """
        self.common_folder_name = common_folder_name
        self.target_dir_name = target_dir_name
        self.balena_command_args = balena_command_args

        self.current_dir = os.getcwd()
        self.target_dir = os.path.join(self.current_dir, self.target_dir_name)
        self.common_dir = os.path.join(self.current_dir, self.common_folder_name)
        self.dst_common_dir = os.path.join(self.target_dir, self.common_folder_name)

        # Optional colorama for colored output
        try:
            from colorama import Fore, Style

            self.colorama_installed = True
            self.Fore = Fore
            self.Style = Style
        except ImportError:
            self.colorama_installed = False
            self.Fore = None
            self.Style = None

    def compare_common_dirs(self, dir1, dir2):
        """
        Recursively compare two directories and return a list of differences.

        Args:
            dir1 (str): Path to the first directory.
            dir2 (str): Path to the second directory.

        Returns:
            list: A list of differences between the directories.
        """
        differences = []
        dirs_cmp = filecmp.dircmp(dir1, dir2)
        # Files that differ
        for file_name in dirs_cmp.diff_files:
            differences.append(f"Files differ: {os.path.join(dir1, file_name)} and {os.path.join(dir2, file_name)}")
        # Files only in dir1
        for file_name in dirs_cmp.left_only:
            differences.append(f"File only in original {self.common_folder_name} folder: {os.path.join(dir1, file_name)}")
        # Files only in dir2
        for file_name in dirs_cmp.right_only:
            differences.append(f"File only in '{dir2}' folder: {os.path.join(dir2, file_name)}")
        # Recursively compare subdirectories
        for sub_dir in dirs_cmp.common_dirs:
            sub_differences = self.compare_common_dirs(os.path.join(dir1, sub_dir), os.path.join(dir2, sub_dir))
            differences.extend(sub_differences)
        return differences

    def compare_common_dirs_main(self):
        """
        Compare the original and destination common directories and decide whether to proceed.

        Returns:
            bool: True if it's safe to proceed, False otherwise.
        """
        differences = self.compare_common_dirs(self.common_dir, self.dst_common_dir)
        if differences:
            if self.colorama_installed:
                print(
                    self.Fore.RED
                    + f"Error: {self.common_folder_name} folder already exists in '{os.path.dirname(self.dst_common_dir)}', and there are differences between the original and the copied folder."
                    + self.Style.RESET_ALL
                )
            else:
                print(f"Error: {self.common_folder_name} folder already exists in '{os.path.dirname(self.dst_common_dir)}', and there are differences between the original and the copied folder.")
            print("Differences found:")
            for diff in differences:
                print(diff)
            return False  # Do not proceed
        else:
            print(f"Warning: {self.common_folder_name} folder already exists in '{os.path.dirname(self.dst_common_dir)}', but the files are the same. Proceeding.")
            return True  # Proceed

    def compare_and_handle_on_exit(self):
        """
        Compare the common directories upon exit and handle the copied folder accordingly.
        """
        differences = self.compare_common_dirs(self.common_dir, self.dst_common_dir)
        if differences:
            # Differences found; do not delete the copied 'common' folder
            if self.colorama_installed:
                print(self.Fore.RED + f"Warning: Changes were made to the {self.common_folder_name} folder in '{os.path.dirname(self.dst_common_dir)}'. It will not be deleted." + self.Style.RESET_ALL)
            else:
                print(f"Warning: Changes were made to the {self.common_folder_name} folder in '{os.path.dirname(self.dst_common_dir)}'. It will not be deleted.")
            print("Differences found:")
            for diff in differences:
                print(diff)
        else:
            # No differences; safe to delete the copied 'common' folder
            if os.path.exists(self.dst_common_dir):
                shutil.rmtree(self.dst_common_dir)
                print(f"Removed {self.common_folder_name} folder from '{os.path.basename(self.dst_common_dir)}'.")
            else:
                print(f"No {self.common_folder_name} folder to remove from '{os.path.basename(self.dst_common_dir)}'.")

    def copy_common_dir(self):
        """
        Copy the common directory to the target directory.
        """
        # Remove the existing 'common' folder in target directory if it exists
        if os.path.exists(self.dst_common_dir):
            shutil.rmtree(self.dst_common_dir)
        # Copy the 'common' folder
        shutil.copytree(self.common_dir, self.dst_common_dir)

    def run_balena_command(self):
        """
        Run the Balena CLI command in the target directory.
        """
        # Build the Balena CLI command
        balena_command = ["balena"] + self.balena_command_args
        # Set the working directory to the target directory
        subprocess.run(balena_command, cwd=self.target_dir)

    def execute(self):
        """
        Execute the main logic of copying the common directory, running the Balena command,
        and handling the common directory upon exit.
        """
        # Check if target directory exists
        if not os.path.isdir(self.target_dir):
            print(f"Error: Target directory '{self.target_dir_name}' does not exist.")
            sys.exit(1)

        # Step 1: Check if 'common' directory exists in target directory
        if os.path.exists(self.dst_common_dir):
            proceed = self.compare_common_dirs_main()
            if not proceed:
                # Exit the script due to differences
                sys.exit(1)
        else:
            # No existing 'common_folder_name' folder in the target directory
            pass

        try:
            # Step 2: Copy the 'common_folder_name' directory into the target directory
            self.copy_common_dir()

            # Step 3: Run the Balena CLI command
            self.run_balena_command()
        except KeyboardInterrupt:
            # Handle graceful shutdown (Ctrl+C)
            print("\nScript interrupted by user.")
        finally:
            # Compare and handle the 'common' folder upon exit
            self.compare_and_handle_on_exit()


if __name__ == "__main__":

    # Command-line parsing
    if len(sys.argv) < 2:
        print("Usage: python cli_wrapper.py <target_directory> [balena_command] [balena_args]")
        # Example: python cli_wrapper.py jetson_runtime push 192.168.1.100 --debug
        sys.exit(1)

    target_dir_name = sys.argv[1]
    balena_command_args = sys.argv[2:]
    common_folder_name = "BYODR_utils"

    if not balena_command_args:
        print("Error: No Balena CLI command provided.")
        print("Usage: python cli_wrapper.py <target_directory> [balena_command] [balena_args]")
        sys.exit(1)

    # Create an instance of CLIWrapper
    cli_wrapper = CLIWrapper(common_folder_name, target_dir_name, balena_command_args)

    # Execute the main logic
    cli_wrapper.execute()
