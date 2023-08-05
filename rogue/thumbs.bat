@echo off
setlocal

REM Set the path to the GraphicsMagick installation directory
set "GM_DIR=C:\Path\to\GraphicsMagick"

REM Set the source and destination folder paths
set "SOURCE_FOLDER=art"
set "DESTINATION_FOLDER=display"

REM Create the destination folder if it doesn't exist
if not exist "%DESTINATION_FOLDER%" mkdir "%DESTINATION_FOLDER%"

REM Change to the source folder
cd "%SOURCE_FOLDER%"

REM Loop through each file in the source folder and resize using GraphicsMagick
for %%G in (*) do (
  "gm" convert "%%G" -resize 100x100 "../%DESTINATION_FOLDER%/%%~nxG"
)

REM Return to the original folder
cd ..

echo Image resizing complete.
pause
