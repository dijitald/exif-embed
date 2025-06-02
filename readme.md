# Exif-Embed Tool

## Overview
The **Exif-Embed Tool** is designed to process media files by extracting metadata from JSON files and embedding it into media files such as images and videos. It also provides functionality to organize and upload files to cloud storage or local directories using **rclone**.

## Features
- **Metadata Embedding**: Extract metadata from JSON files and embed it into media files using **ExifTool**.
- **File Organization**: Move or copy files to local directories or upload them to cloud storage (e.g., OneDrive) using **rclone**.
- **Cleanup**: Remove unnecessary files from the source directory after processing.
- **Interactive Mode**: Allows users to choose destinations and target directories interactively.

## Requirements
### ExifTool
ExifTool is required for embedding metadata into media files. You can download and install ExifTool from the official website:  
[ExifTool Official Website](https://exiftool.org/)

### Rclone
Rclone is required for uploading files to cloud storage. Ensure that Rclone is installed and configured properly. You can download and set up Rclone from the official website:  
[Rclone Official Website](https://rclone.org/)

## Usage
1. **Unzip Media Files**: Place your `.zip` files in the `zips` folder. The tool will extract them into the `extracts` folder.
2. **Embed Metadata**: The tool will process the extracted files, find matching JSON metadata, and embed it into the media files.
3. **Organize Files**: Choose whether to move/copy files to a local directory or upload them to cloud storage.
4. **Cleanup**: The tool will remove unnecessary files after processing.

## Running the Tool
Run the tool using the following command:
```bash
python extract_and_embed.py
```

## Logging
The tool provides detailed logs for debugging and tracking the processing steps.

## License
This project is licensed under the MIT License.

For further assistance, refer to the documentation or contact the project maintainer.  