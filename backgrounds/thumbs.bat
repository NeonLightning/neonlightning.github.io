@echo off
setlocal

REM Set the source and destination folder paths
set "SOURCE_FOLDER=art"
set "DESTINATION_FOLDER=display"

REM Check if the destination folder exists, and create it if it doesn't
if not exist "%DESTINATION_FOLDER%" (
    mkdir "%DESTINATION_FOLDER%"
    echo Destination folder "%DESTINATION_FOLDER%" created.
) else (
    echo Destination folder "%DESTINATION_FOLDER%" already exists.
)

REM Set the path to the ImageMagick convert executable
set "IM_CONVERT=convert.exe"

REM Change the current directory to the source folder
cd "%SOURCE_FOLDER%"
echo Changed directory to source folder: %cd%

REM Loop through each file in the source folder and resize using ImageMagick
for %%G in (*) do (
    echo Resizing file: %%G
    "%IM_CONVERT%" "%%G" -resize 100x100^> "../%DESTINATION_FOLDER%/%%~nG%%~xG"
    echo Resized and copied to "%DESTINATION_FOLDER%/%%~nG%%~xG"
)

REM Return to the original folder
cd ..
echo Returned to the original folder: %cd%

echo Image resizing complete.
pause
