import sys
import os, zipfile, argparse
from logger_utils import Colors, setup_logging

logger = setup_logging(script_name='exif-embed-extract')

def main():
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description='Extract ZIP files from source folder to target folder')
    parser.add_argument('--source', '-s', 
                       default='./zips', 
                       help='Source folder containing ZIP files (default: ./zips)')
    parser.add_argument('--target', '-t', 
                       default='./extracts', 
                       help='Target folder for extraction (default: ./extracts)')
    
    args = parser.parse_args()
    zip_folder = args.source
    extract_to = args.target

    try:
        logger.info(f"Unzipping files in {Colors.CYAN}{zip_folder}{Colors.RESET}")
 
        for item in os.listdir(zip_folder):
            if item.endswith('.zip'):
                file_path = os.path.join(zip_folder, item)
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_to)
                logger.info(f"Extracted: {file_path}")

        logger.info(f"Unzipped files to {Colors.CYAN}{extract_to}{Colors.RESET}")
        
    except Exception as e:
        logger.error(f"Process failed: {str(e)}")


if __name__ == "__main__":
    # Enable Windows color support
    if os.name == 'nt':
        os.system('color')
        
    # Run the main program
    sys.exit(main())
