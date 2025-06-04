import datetime
import os
import subprocess
import sys
import argparse
from logger_utils import Colors, setup_logging
import win32file
import win32con
import pywintypes

logger = setup_logging(script_name='exif-embed-update-creation-date')

def update_creation_date():
    parser = argparse.ArgumentParser(description="Update the creation date of media files based on metadata JSON files.")
    parser.add_argument("--source", "-s", default="./extracts/Takeout/Google Photos", 
                        help="Source directory containing files (default: ./extracts/Takeout/Google Photos)")
    args = parser.parse_args()
    root_folder = args.source

    for subdir, _, files in os.walk(root_folder):
        logger.info(f"Processing directory: {Colors.CYAN}{subdir}{Colors.RESET}")        
        for file in files:
            try:
                if file.lower().endswith('.mp4'):
                    continue

                image_date = None
                file_date = os.path.getctime(os.path.join(subdir, file))
                file_date = datetime.datetime.fromtimestamp(file_date).strftime('%Y:%m:%d %H:%M:%S')
                exiftool_cmd = [
                    'exiftool',
                    '-s',  # Short output
                    '-DateTimeOriginal',  # Get the original date taken
                    os.path.join(subdir, file)
                ]
                result = subprocess.run(exiftool_cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    image_date = result.stdout.strip().split(': ')[1].strip() if result.stdout else None
                    if image_date:
                        image_date = image_date.split('-')[0].split('+')[0].strip()

                if image_date and image_date.split()[0].strip() != file_date.split()[0].strip():
                    print(f"Updating {file} creation date from {file_date} to {image_date}")
                    try :
                        image_date = datetime.datetime.strptime(image_date, '%Y:%m:%d %H:%M:%S')
                    except ValueError:
                        logger.error(f"Invalid date format for {file}: {image_date} : {result.stdout.strip()}")
                        continue

                    win_time = pywintypes.Time(image_date)
                    handle = win32file.CreateFile(
                        os.path.join(subdir, file),
                        win32con.GENERIC_WRITE,
                        win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
                        None,
                        win32con.OPEN_EXISTING,
                        win32con.FILE_ATTRIBUTE_NORMAL,
                        None
                    )
                    win32file.SetFileTime(handle, win_time, None, None)
                    handle.close()

            except Exception as e:
                logger.exception(f"Failed to process {file}: {str(e)}")


if __name__ == "__main__":
    if os.name == 'nt':
        os.system('color')
    sys.exit(update_creation_date())