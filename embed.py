import argparse
import sys
import os, json, subprocess, re, datetime
from logger_utils import Colors, setup_logging
import win32file
import win32con
import pywintypes

logger = setup_logging(script_name='exif-embed-embed')

def find_json_file(media_file, json_files):
    for json_file in json_files:
        if json_file.startswith(media_file) and json_file.endswith('.json'):
            logger.debug(f"Found matching JSON file '{json_file}' for media file '{media_file}'")
            return json_file
    
    logger.debug(f"No matching JSON file found for '{media_file}'")
    return None

def clean_date_string(date_str):
    """
    function to identify/remove any special/invisible characters in date strings
    """
    import string
    printable_chars = set(string.printable)
    cleaned = ''.join(c for c in date_str if c in printable_chars) # Cleaned version with only printable ASCII
    cleaned_nbsp = cleaned.replace('\xa0', ' ') # Attempt to clean non-breaking space (common in date formats)
    normalized = re.sub(r'\s+', ' ', cleaned_nbsp)
    return normalized

def format_date_for_exiftool(photo_taken_data):
    """
    Convert Google Photos date format to the format expected by ExifTool
    ExifTool expects dates in format: YYYY:MM:DD HH:MM:SS

    param photo_taken_data: Dictionary containing photo taken time information
    """
    if not photo_taken_data:
        return None

    timestamp = photo_taken_data.get('timestamp')
    date_str = clean_date_string(photo_taken_data.get('formatted', ''))
    logger.debug(f"timestamp:date_str [{timestamp} : {date_str}]")

    if timestamp and timestamp.isdigit():
        # Convert Unix timestamp to datetime
        try:
            timestamp_value = int(timestamp)
            dt = datetime.datetime.fromtimestamp(timestamp_value)
            date_taken = dt.strftime('%Y:%m:%d %H:%M:%S')
            logger.debug(f"Using timestamp value: {timestamp} -> {date_taken}")
            return date_taken
        except (ValueError, OverflowError) as e:
            logger.warning(f"Failed to convert timestamp {timestamp}: {e}")
    elif date_str:
        cleaned_date_str = clean_date_string(date_str)
        logger.debug(f"Using formatted and cleaned date string: {cleaned_date_str}")

        # Specifically handle Google Photos format: "Sep 24, 2022, 10:45:55 PM UTC"
        utc_pattern = re.compile(r'([A-Za-z]{3} \d{1,2}, \d{4}, \d{1,2}:\d{2}:\d{2} [AP]M) UTC')
        utc_match = utc_pattern.search(cleaned_date_str)
        
        if utc_match:
            date_part = utc_match.group(1)  # "Sep 24, 2022, 10:45:55 PM"
            try:
                dt = datetime.datetime.strptime(date_part, '%b %d, %Y, %I:%M:%S %p')
                return dt.strftime('%Y:%m:%d %H:%M:%S')
            except ValueError as e:
                logger.debug(f"Failed to parse Google Photos date format: {cleaned_date_str} - {e}")
        
    return None #datetime.datetime.now().strftime('%Y:%m:%d %H:%M:%S')

def extract_people_tags(metadata):
    """
    Extract people names from metadata to use as tags
    """
    people_tags = []
    if 'people' in metadata and isinstance(metadata['people'], list):
        for person in metadata['people']:
            if 'name' in person and person['name']:
                people_tags.append(person['name'])
    return people_tags

def set_file_date(subdir, media_file, image_date):
    try:
        #remove any timezone or extra characters from the date string
        image_date = image_date.split('-')[0].split('+')[0].strip()

        file_date = os.path.getctime(os.path.join(subdir, media_file))
        file_date = datetime.datetime.fromtimestamp(file_date).strftime('%Y:%m:%d %H:%M:%S')
        if image_date.split()[0].strip() != file_date.split()[0].strip():
            try :
                try:
                    image_date = datetime.datetime.strptime(image_date, '%Y:%m:%d %H:%M:%S.%f')
                except ValueError:
                    image_date = datetime.datetime(year=1973, month=12, day=21, hour=0, minute=0, second=0)
            except ValueError:
                logger.error(f"Invalid date format for {media_file}: {image_date}")
                return
            
            win_time = pywintypes.Time(image_date)
            handle = win32file.CreateFile
            (
                os.path.join(subdir, media_file),
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
        logger.error(f"Failed to set file date for {media_file}: {e}")

def embed_metadata(root_folder):
    for subdir, _, files in os.walk(root_folder):
        media_files = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.mp4', '.mov', '.heic'))]
        json_files = [f for f in files if f.lower().endswith('.json')]

        logger.info(f"Processing directory: {Colors.CYAN}{subdir}{Colors.RESET}")
        logger.debug(f"Found {len(media_files)} media files and {len(json_files)} JSON files")
        
        for media_file in media_files:
            try:
                json_file = find_json_file(media_file, json_files)
                if json_file:
                    with open(os.path.join(subdir, json_file), 'r', encoding='utf-8') as f:
                        metadata = json.load(f)

                    title = metadata.get('title', '')
                    description = metadata.get('description', '')
                    image_date = format_date_for_exiftool(metadata.get('photoTakenTime', {}))
                    location = metadata.get('geoData', {})
                    latitude = location.get('latitude')
                    longitude = location.get('longitude')
                    altitude = location.get('altitude')
                    make = metadata.get('cameraMake', '')
                    model = metadata.get('cameraModel', '')
                    software = metadata.get('software', '')
                    keywords = metadata.get('keywords', [])
                    copyright = metadata.get('copyright', '')
                    artist = metadata.get('artist', '')
                    
                    people_tags = extract_people_tags(metadata)
                    if people_tags:
                        if keywords:
                            keywords.extend(people_tags)
                        else:
                            keywords = people_tags
                        logger.debug(f"Added people tags: {', '.join(people_tags)}")

                    logger.debug(f"Processing file: {media_file}")
                    
                    # Build the command
                    exiftool_cmd = [
                        'exiftool',
                        '-overwrite_original',  # Don't create backup files
                        '-preserve',           # Preserve file modification date/time
                        f'-Title={title}' if title else None,
                        f'-ImageDescription={description}' if description and media_file.lower().endswith(('.jpg', '.jpeg', '.png', '.mp4', '.mov', '.heic')) else None,
                    ]
                    
                    # Handle date fields
                    if image_date:
                        exiftool_cmd.extend([
                            f'-DateTimeOriginal={image_date}',
                            f'-CreateDate={image_date}', 
                            f'-ModifyDate={image_date}'
                        ])                        
                        set_file_date(subdir, media_file, image_date)
                    
                    # Handle GPS data
                    if latitude and longitude:
                        exiftool_cmd.extend([
                            f'-GPSLatitude={latitude}',
                            f'-GPSLongitude={longitude}',
                        ])
                        # Add GPSLatitudeRef and GPSLongitudeRef
                        if float(latitude) >= 0:
                            exiftool_cmd.append('-GPSLatitudeRef=N')
                        else:
                            exiftool_cmd.append('-GPSLatitudeRef=S')
                            
                        if float(longitude) >= 0:
                            exiftool_cmd.append('-GPSLongitudeRef=E')
                        else:
                            exiftool_cmd.append('-GPSLongitudeRef=W')
                            
                        if altitude:
                            exiftool_cmd.append(f'-GPSAltitude={altitude}')
                    
                    # Add remaining metadata
                    if make:
                        exiftool_cmd.append(f'-Make={make}')
                    if model:
                        exiftool_cmd.append(f'-Model={model}')
                    if software:
                        exiftool_cmd.append(f'-Software={software}')
                    if keywords:
                        exiftool_cmd.append(f'-Keywords={",".join(keywords)}')
                    if copyright:
                        exiftool_cmd.append(f'-Copyright={copyright}')
                    if artist:
                        exiftool_cmd.append(f'-Artist={artist}')
                    
                    # Add the file path at the end
                    exiftool_cmd.append(os.path.join(subdir, media_file))
                    
                    # Clean up None values
                    exiftool_cmd = [arg for arg in exiftool_cmd if arg is not None]
                    
                    # Log the command for debugging
                    logger.debug(f"Running command: {' '.join(exiftool_cmd)}")
                    
                    # Run the command
                    result = subprocess.run(exiftool_cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        logger.info(f"Successfully processed: {os.path.join(subdir, media_file)}")
                        # Log what exiftool actually did
                        if result.stdout:
                            logger.debug(f"Exiftool output: {result.stdout}")                        
                    else:
                        logger.error(f"Error processing {media_file}: {result.stderr}")
                        logger.error(f"Command was: {' '.join(exiftool_cmd)}")
                else:
                    logger.warning(f"No metadata JSON found for: {media_file}")
            except Exception as e:
                logger.exception(f"Failed to process {media_file}: {str(e)}")

def cleanup_files(source_folder):
    #any file that is not one of the designated media files should be deleted
    for root, dirs, files in os.walk(source_folder):
        for file in files:
            if not file.lower().endswith(('.jpg', '.jpeg', '.png', '.mp4', '.mov', '.heic', '.mts', '.wmv', '.avi', '.gif')):
                os.remove(os.path.join(root, file))
                logger.debug(f"Removed extraneous file: {file}")


def main ():
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description='Embed metadata into media files using ExifTool')
    parser.add_argument('--target', '-t', 
                       default='./extracts', 
                       help='Target folder for embedding metadata (default: ./extracts)')

    args = parser.parse_args()
    target_dir = args.target

    try:
        logger.info(f"Starting metadata re-embedding process in {Colors.CYAN}{target_dir}{Colors.RESET}")
        embed_metadata(target_dir)
        cleanup_files(target_dir)
        logger.info(f"{Colors.GREEN}Metadata re-embedding process completed successfully{Colors.RESET}")
    except Exception as e:
        logger.error(f"Process failed: {str(e)}")


if __name__ == "__main__":    
    # Enable Windows color support
    if os.name == 'nt':
        os.system('color')
        
    # Run the main program
    sys.exit(main())
