@echo off
setlocal

REM Set the source and destination folder paths
set "SOURCE_FOLDER=art"
set "DESTINATION_FOLDER=display"

REM Create the destination folder if it doesn't exist
if not exist "%DESTINATION_FOLDER%" mkdir "%DESTINATION_FOLDER%"

REM Set the path to the ImageMagick convert executable
set "IM_CONVERT=D:\programs\imagemagick\convert.exe"

REM Change to the source folder
cd "%SOURCE_FOLDER%"

REM Loop through each file in the source folder and resize using ImageMagick
for %%G in (*) do (
  "%IM_CONVERT%" "%%G" -resize 100x100^> "../%DESTINATION_FOLDER%/%%~nG%%~xG"
)

REM Return to the original folder
cd ..

echo Image resizing complete.
pause