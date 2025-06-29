
@echo off
python3 proces_media_files.py %*
python3 update_creation_date.py %*
pause
