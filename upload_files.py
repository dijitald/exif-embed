import os, subprocess, logging, argparse, sys, shutil
from logger_utils import Colors, setup_logging
from  tqdm import tqdm

logger = setup_logging(script_name='media_processor')

def check_rclone():
    """Check if rclone is available and properly configured"""
    try:
        # Check if rclone executable exists in the script directory or system path
        rclone_path = "rclone.exe" if os.path.exists("rclone.exe") else "rclone"
        
        # Run rclone version to check if it's working
        result = subprocess.run([rclone_path, "version"], 
                               capture_output=True, 
                               text=True, 
                               check=True)
        logger.debug(f"Rclone version: {result.stdout.splitlines()[0]}")
        
        # List remotes to check configuration
        remotes = subprocess.run([rclone_path, "listremotes"], 
                                capture_output=True, 
                                text=True, 
                                check=True)
        
        if not remotes.stdout.strip():
            logger.error(f"{Colors.BRIGHT_RED}No rclone remotes found. Please configure OneDrive remote first.{Colors.RESET}")
            logger.info("Run 'rclone config' to set up your OneDrive remote")
            return False, rclone_path
        
        logger.debug(f"Available remotes: {remotes.stdout}")
        return True, rclone_path
        
    except subprocess.CalledProcessError as e:
        logger.error(f"{Colors.BRIGHT_RED}Error checking rclone: {e}{Colors.RESET}")
        logger.error(f"Stderr: {e.stderr}")
        return False, None
    except FileNotFoundError:
        logger.error(f"{Colors.BRIGHT_RED}Rclone not found. Please install rclone and ensure it's in your PATH.{Colors.RESET}")
        return False, None

def upload_to_onedrive(source_dir, target_path, remote, rclone_path):
    """
    Upload files to OneDrive using rclone while preserving directory structure
    
    Args:
        files: List of files to upload
        remote: Rclone remote name (e.g., 'onedrive')
        target_path: Target folder on the remote
        rclone_path: Path to the rclone executable
        source_dir: Source directory to use as base for preserving folder structure
    """ 
    if not os.path.isdir(source_dir):
        logger.error(f"{Colors.BRIGHT_RED}Source directory '{source_dir}' does not exist{Colors.RESET}")
        return False
    
    try:
        file_cmd = f'dir /s /b /a-d "{source_dir}" | find /c /v ""'
        file_output = subprocess.check_output(file_cmd, shell=True, text=True)
        file_count = int(file_output.strip())
        logger.info(f"{Colors.BRIGHT_GREEN}Starting upload of {file_count} files in directory {source_dir} to OneDrive{Colors.RESET}")

        pbar = tqdm(total=file_count, desc="Uploading files", unit="file", dynamic_ncols=True)
        # Build the rclone command with progress option
        cmd = [
            rclone_path, 
            "copy", 
            "-v",
            "--transfers", "4",  # Number of file transfers to run in parallel
            source_dir,  
            f"{remote}:{target_path}"  # Destination
        ]

        logger.debug(f"Running command: {' '.join(cmd)}")
        
        # Run the command and stream output in real-time
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Process and log output in real-time
        for line in process.stdout:
            line = line.strip()
            if line:
                if "ERROR" in line:
                    logger.error(line)
                elif "copied:" in line or "Copied:" in line:
                    pbar.update(1)
                    logger.info(f"{Colors.BRIGHT_BLUE}{line}{Colors.RESET}")
                elif "There was nothing to transfer" in line:
                    pbar.update(file_count - pbar.n)  # Complete the progress bar if no files to transfer
                else:
                    logger.debug(line)
        
        process.wait()
            
    except Exception as e:
        logger.error(f"{Colors.BRIGHT_RED}Error during upload: {str(e)}{Colors.RESET}")

    finally:
        pbar.close()
        if process.returncode == 0:
            logger.info(f"{Colors.BRIGHT_GREEN}Upload completed successfully{Colors.RESET}")
        else:
            logger.error(f"{Colors.BRIGHT_RED}Upload failed with return code {process.returncode}{Colors.RESET}")

def process_files(source_dir, destination, **kwargs):
    """
    Copy / Move all files and directories to the target location.

    Args:
        source_dir: Source directory to search for files. The full directory structure will be preserved.
        destination: Either 'onedrive' or 'pictures', determines where to send files
        kwargs: Additional arguments:
            - target_dir: Target directory on OneDrive
            - operation: Either 'move' or 'copy', only used if target is Pictures.
                
            - rclone_path: Path to the rclone executable
            - rclone_remote: Rclone remote name which was setup by running `rclone config`
    Returns:
        List of found files, or success status if target_folder is provided

    """
    logger.debug(f"Processing files in {source_dir}")
    
    if not os.path.isdir(source_dir):
        logger.error(f"{Colors.BRIGHT_RED}Source directory '{source_dir}' does not exist{Colors.RESET}")
        return False

    target_dir = kwargs.get('target_dir')
    if destination == 'onedrive':
        rclone_path = kwargs.get('rclone_path')        
        rclone_remote = kwargs.get('rclone_remote')
        logger.info(f"{Colors.BRIGHT_GREEN}Uploading files to OneDrive : {target_dir}{Colors.RESET}")
        return upload_to_onedrive(source_dir, target_dir, rclone_remote, rclone_path)
    
    if destination == 'pictures':
        operation = kwargs.get('operation')
        operation_verb = "moving" if operation == "move" else "copying"
        if operation not in ['move', 'copy']:
            logger.error(f"{Colors.BRIGHT_RED}Invalid operation type '{operation}'. Must be 'move' or 'copy'.{Colors.RESET}")
            return False
        
        target_dir = os.path.join(os.path.expanduser('~\\Pictures'), target_dir)
        is_same_drive = os.path.splitdrive(os.path.abspath(source_dir))[0].lower() == os.path.splitdrive(os.path.abspath(target_dir))[0].lower()
        success_count = 0
        error_count = 0

        for root, _, files in os.walk(source_dir):
            for source_file in files:
                source_file = os.path.join(root, source_file)
                try:
                    # source_abs_path = os.path.abspath(file)
                    # src_rel_path = os.path.relpath(source_abs_path, src)
                    # dest_rel_path = os.path.relpath(os.path.join(target, src_rel_path))
                    # dest_abs_path = os.path.abspath(dest_rel_path)

                    dest_file = os.path.join(target_dir, os.path.relpath(source_file, start=source_dir))
                    if os.path.exists(dest_file):
                        logger.warning(f"{Colors.YELLOW}File already exists: {dest_file}. Skipping.{Colors.RESET}")
                        continue
                    logger.debug(f"{operation_verb.capitalize()} file: {source_file} to {dest_file}")

                    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                    if operation == 'copy':
                        shutil.copy2(source_file, dest_file)
                        logger.debug(f"Copied: {source_file} to {dest_file}")
                    else:  # move operation
                        if is_same_drive:
                            # On same drive, use rename (efficient move operation)
                            os.rename(source_file, dest_file)
                            logger.debug(f"Moved: {source_file} to {dest_file}")
                        else:
                            # Cross-drive move requires copy then delete
                            shutil.copy2(source_file, dest_file)
                            os.remove(source_file)
                            logger.debug(f"Cross-drive move: {source_file} to {dest_file}")
            
                    success_count += 1
                
                except Exception as e:
                    logger.error(f"{Colors.RED}Failure {operation_verb} {source_file}: {str(e)}{Colors.RESET}")
                    error_count += 1

        # Log success and error counts
        past_tense = "moved" if operation == "move" else "copied"
        if success_count > 0:
            logger.info(f"{Colors.BRIGHT_GREEN}Successfully {past_tense} {success_count} files to {target_dir}{Colors.RESET}")
        if error_count > 0:
            logger.warning(f"{Colors.YELLOW}Failed to {past_tense} {error_count} files{Colors.RESET}")
        return success_count > 0
    
    # # Try to determine a common base directory
    # try:
    #     common_prefix = os.path.commonpath([os.path.abspath(f) for f in all_files])
    #     # Only use it as source_dir if it's a directory
    #     if os.path.isdir(common_prefix):
    #         source_base_dir = common_prefix
    #         logger.debug(f"Detected common source directory: {source_base_dir}")
    #     else:
    #         source_base_dir = source_dir
    # except ValueError:
    #     # Files don't share a common prefix
    #     logger.debug("No common source directory detected")
    #     source_base_dir = source_dir   

def main():
    parser = argparse.ArgumentParser(description="Process and move/upload files")
    parser.add_argument("--source", "-s", default="./extracts/Takeout/Google Photos", 
                        help="Source directory containing files (default: ./extracts/Takeout/Google Photos)")
    parser.add_argument("--destination", "-d", choices=["onedrive", "pictures"],
                        help="Choose where to send files: 'onedrive' or 'pictures' folder")
    parser.add_argument("--remote", "-r", default="onedrive",
                        help="Rclone remote name (default: onedrive)")
    parser.add_argument("--target", "-t",
                        help="Target folder on OneDrive or in Pictures Library (leave empty for root folder)")
    parser.add_argument("--operation", "-o", choices=["move", "copy"], default='copy',
                        help="Choose whether to 'move' or 'copy' files when using Pictures destination (OneDrive is always copy)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose output")
    
    args = parser.parse_args()
    source_dir = os.path.abspath(args.source)
    destination = args.destination.lower() if args.destination else None
    rclone_remote = args.remote # (default: onedrive)
    target_dir = args.target
    operation = args.operation # (move or copy)
    rclone_path = None  # Will be set if rclone is available
    
    # Set log level based on verbose flag
    if args.verbose:
        for handler in logging.getLogger().handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                handler.setLevel(logging.DEBUG)

    logger.info(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}File Processor{Colors.RESET}")
    
    # Check if source directory exists
    if not os.path.isdir(source_dir):
        logger.error(f"{Colors.BRIGHT_RED}Source directory '{source_dir}' does not exist{Colors.RESET}")
        return 1
    
    if not destination:
        # Interactive mode - ask user for destination        
        print(f"\n{Colors.BOLD}Choose destination for files:{Colors.RESET}")
        print(f"  1. {Colors.CYAN}Pictures library{Colors.RESET} (local)")
        print(f"  2. {Colors.CYAN}OneDrive{Colors.RESET} (cloud)")
        
        while True:
            choice = input(f"\n{Colors.YELLOW}Enter your choice (1/2): {Colors.RESET}").strip()
            if choice == '1':
                destination = 'pictures'
                break
            elif choice == '2':
                destination = 'onedrive'
                break
            else:
                print(f"{Colors.RED}Invalid choice. Please enter 1 or 2.{Colors.RESET}") 
    if not target_dir:
        # Interactive mode - ask user for target directory
        if destination == 'onedrive':
            target_dir = input(f"{Colors.YELLOW}Enter target folder on OneDrive (e.g. Pictures): {Colors.RESET}").strip() or ""
        elif destination == 'pictures':
            target_dir = input(f"{Colors.YELLOW}Enter target folder in Pictures Library (leave empty for root folder): {Colors.RESET}").strip() or ""

    if destination == 'pictures':
        target_dir = os.path.join(os.path.expanduser('~\\Pictures'), target_dir)
        operation_verb = "Moving" if operation == "move" else "Copying"
        logger.info(f"{operation_verb} files to {Colors.CYAN}{target_dir}{Colors.RESET}")    
    
    elif destination == 'onedrive':
        # Check if rclone is available and configured
        rclone_available, rclone_path = check_rclone()        
        if not rclone_available:
            # Run rclone config in interactive mode
            logger.info("Running rclone configuration...")            
            try:
                subprocess.run([rclone_path if rclone_path else "rclone", "config"], check=True)
                
                # Check again if configuration worked
                rclone_available, rclone_path = check_rclone()
                if not rclone_available:
                    logger.error(f"{Colors.BRIGHT_RED}Rclone configuration failed or no remotes were added.{Colors.RESET}")
                    return 1
            except Exception as e:
                logger.error(f"{Colors.BRIGHT_RED}Failed to run rclone config: {str(e)}{Colors.RESET}")
                return 1

    success = process_files(source_dir, destination, target_dir=target_dir, operation=operation, rclone_remote=rclone_remote, rclone_path=rclone_path)
    return success if success else 1

if __name__ == "__main__":
    # Enable Windows color support
    if os.name == 'nt':
        os.system('color')
        
    # Run the main program
    sys.exit(main())
