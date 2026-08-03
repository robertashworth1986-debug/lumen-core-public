@echo off
if "%~1"=="-Z1" (
  tar -tf "%~2"
  exit /b 0
)
if "%~1"=="-p" (
  tar -xOf "%~2" "%~3"
  exit /b 0
)
echo Unsupported unzip compatibility arguments 1>&2
exit /b 2
