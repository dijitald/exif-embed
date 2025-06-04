import argparse
import os
import sys
from logger_utils import Colors, setup_logging

logger = setup_logging(script_name='exif-embed-scrub-live-files')

def scrub():
    parser = argparse.ArgumentParser(description="Cleanup MP4 live photo files")
    parser.add_argument("--source", default="./extracts", help="Root folder containing media files (default: ./extracts)")
    parser.add_argument("--target", default="./livefiles", help="Target folder for extracted files (default: ./livefiles)")
    args = parser.parse_args()
    source_dir = args.source
    target_dir = args.target

    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.lower().endswith('.mp4'):
                print (f"Processing file: {file}")
                heic_path = f"{os.path.splitext(file)[0]}.heic"

                #if the file exists, move the mp4 file
                if os.path.exists(os.path.join(root, heic_path)):
                    source_file = os.path.join(root, file)
                    dest_file = os.path.join(target_dir, os.path.relpath(source_file, start=source_dir))
                    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                    logger.debug (f"moving '{source_file}' to '{dest_file}'")
                    os.rename(source_file, dest_file)

    logger.info(f"Scrubbing complete in {Colors.CYAN}{source_dir}{Colors.RESET}")
    return 0

if __name__ == "__main__":
    if os.name == 'nt':
        os.system('color')
    sys.exit(scrub())