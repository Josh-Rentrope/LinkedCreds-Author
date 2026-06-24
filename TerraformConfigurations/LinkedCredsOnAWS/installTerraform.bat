@echo off
title Terraform Installer for Windows
cd /d "%~dp0"

:: ------------------------------------------------------------------
:: Check for admin rights
:: ------------------------------------------------------------------
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ============================================================
    echo This script needs Administrator access.
    echo ============================================================
    echo.
    echo Right-click this file and select "Run as administrator"
    echo.
    pause
    exit /b 1
)

echo ============================================================
echo Terraform Installer for Windows
echo ============================================================
echo.

:: Check if already installed
where terraform >nul 2>&1
if %errorLevel% equ 0 (
    echo Terraform is already installed at:
    where terraform
    echo.
    pause
    exit /b 0
)

:: ------------------------------------------------------------------
:: Step 1 – Detect latest version from GitHub API
:: ------------------------------------------------------------------
echo [1/4] Detecting latest Terraform version...

:: Download the GitHub API response as JSON
curl.exe -s -o "%TEMP%\tf_release.json" https://api.github.com/repos/hashicorp/terraform/releases/latest


if not exist "%TEMP%\tf_release.json" (
    echo Failed to reach GitHub. Using fallback version 1.10.5
    set "TF_VERSION=1.10.5"
) else (
    call :GetLatestVersion
)

del "%TEMP%\tf_release.json" >nul 2>&1

:: Step 2 – Download the Windows ZIP
:: ------------------------------------------------------------------
:: ------------------------------------------------------------------
set "ARCH=amd64"
set "DOWNLOAD_URL=https://releases.hashicorp.com/terraform/%TF_VERSION%/terraform_%TF_VERSION%_windows_%ARCH%.zip"

echo [2/4] Downloading ...
echo   %DOWNLOAD_URL%

curl.exe -# -o "%TEMP%\terraform.zip" "%DOWNLOAD_URL%"
if %errorLevel% neq 0 (
    echo Download failed. Check your internet connection.
    pause
    exit /b 1
)

:: ------------------------------------------------------------------
:: Step 3 – Extract to C:\Terraform
:: ------------------------------------------------------------------
echo [3/4] Extracting to C:\Terraform ...


if exist "C:\Terraform" rmdir /s /q "C:\Terraform" 2>nul
if not exist "C:\Terraform" mkdir "C:\Terraform"


tar -xf "%TEMP%\terraform.zip" -C "C:\Terraform"

:: Verify terraform.exe exists
if not exist "C:\Terraform\terraform.exe" (
    echo Extracted but terraform.exe not found in C:\Terraform.
    dir "C:\Terraform"
    pause
    exit /b 1
)

:: ------------------------------------------------------------------
:: Step 4 – Add to system PATH (permanently, using reg)
:: ------------------------------------------------------------------
echo [4/4] Adding to system PATH ...

:: Read current PATH from registry
for /f "skip=2 tokens=3*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "CURRENT_PATH=%%a%%b"

echo "%CURRENT_PATH%" | findstr /i /c:"C:\Terraform" >nul
if %errorLevel% neq 0 (
    set "NEW_PATH=%CURRENT_PATH%;C:\Terraform"
    reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path /t REG_EXPAND_SZ /d "%NEW_PATH%" /f >nul
    echo   Added C:\Terraform to system PATH
) else (
    echo   C:\Terraform already in PATH
)

:: Broadcast the change to the system
powershell -NoProfile -Command "& { [Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'Machine'), 'Process') }" >nul 2>&1

:: Update this session's PATH too
set "PATH=%PATH%;C:\Terraform"

:: ------------------------------------------------------------------
:: Verify
:: ------------------------------------------------------------------
echo.
echo Verifying installation ...

C:\Terraform\terraform.exe --version >nul 2>&1
if %errorLevel% equ 0 (
    echo ============================================================
    echo  SUCCESS! Terraform %TF_VERSION% installed.
    echo ============================================================
    echo.
    echo   Location: C:\Terraform\terraform.exe
    echo.
    echo   Open a NEW Command Prompt window and run:
    echo     terraform --version
    echo.
) else (
    echo Something went wrong. Check C:\Terraform\terraform.exe
)

:: Clean up
del "%TEMP%\terraform.zip" >nul 2>&1

pause
exit /b

:GetLatestVersion
:: 1. Extract the raw JSON value
for /f "usebackq tokens=2 delims=:, " %%a in (`findstr "tag_name" "%TEMP%\tf_release.json"`) do (
    set "RAW=%%a"
)

echo %RAW%;

:: 2. Strip the double quotes
set "TF_VERSION=%RAW:"=%"

:: 3. Strip the 'v' (e.g., v1.5.0 becomes 1.5.0)
set "TF_VERSION=%TF_VERSION:v=%"

:: 4. Remove trailing comma if present
echo here 3;
if "%TF_VERSION:~-1%"=="," set "TF_VERSION=%TF_VERSION:~0,-1%"

echo    Latest version: %TF_VERSION%

:: Return to the main script
exit /b