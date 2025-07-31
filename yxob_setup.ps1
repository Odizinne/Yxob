# Define necessary paths
$yxobZipUrl = "https://github.com/Odizinne/Yxob/archive/refs/heads/main.zip"
$yxobExtractPath = "$env:LOCALAPPDATA\Programs\Yxob-main"  # Correct path for Yxob-main directory
$pythonInstaller = "python-3.13.3-amd64.exe"
$pythonVersion = "3.13.3"
$pythonPath = "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe"
$venvPath = "$yxobExtractPath\venv"
$venvPythonPath = "$venvPath\Scripts\python.exe"
$venvPythonwPath = "$venvPath\Scripts\pythonw.exe"
$desktopShortcutName = "Yxob.lnk"
$desktopPath = [System.Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path -Path $desktopPath -ChildPath $desktopShortcutName

# Function to download and extract Yxob repository
function Download-And-Extract-Yxob {
    Write-Host "Downloading Yxob repository from GitHub..."
    $zipFilePath = "$env:TEMP\Yxob-main.zip"

    # Download the ZIP file
    Invoke-WebRequest -Uri $yxobZipUrl -OutFile $zipFilePath

    Write-Host "Extracting Yxob repository..."
    # Extract the ZIP file to the desired path
    Expand-Archive -Path $zipFilePath -DestinationPath $env:LOCALAPPDATA\Programs -Force

    # Clean up the ZIP file
    Remove-Item -Path $zipFilePath -Force
}

# Check if Yxob repository is already downloaded
if (-not (Test-Path $yxobExtractPath)) {
    # If Yxob is not found, download and extract it
    Download-And-Extract-Yxob
} else {
    Write-Host "Yxob repository already exists at $yxobExtractPath"
}

# Change directory to the Yxob repository
Set-Location -Path $yxobExtractPath

# Check if Python is installed
Write-Host "Checking for existing Python installation..."
$python = Get-Command python -ErrorAction SilentlyContinue

if ($python) {
    Write-Host "Python is already installed: $($python.Source)"
} else {
    Write-Host "Python not found. Proceeding to download and install..."

    # Define Python installer URL
    $downloadUrl = "https://www.python.org/ftp/python/$pythonVersion/$pythonInstaller"

    # Download installer if not already downloaded
    if (-not (Test-Path $pythonInstaller)) {
        Write-Host "Downloading Python $pythonVersion..."
        Invoke-WebRequest -Uri $downloadUrl -OutFile $pythonInstaller
    }

    # Install Python silently for the current user and add to PATH
    Write-Host "Installing Python $pythonVersion..."
    Write-Host "This may take a moment..."
    Start-Process -FilePath ".\$pythonInstaller" -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0" -Wait

    # Add expected install path to PATH for this session
    $defaultInstallPath = "$env:LOCALAPPDATA\Programs\Python\Python313"
    $env:Path += ";$defaultInstallPath;$defaultInstallPath\Scripts"

    # Remove the installer after installation
    if (Test-Path $pythonInstaller) {
        Write-Host "Removing Python installer..."
        Remove-Item $pythonInstaller -Force
    }
}

# Create virtual environment if it doesn't exist
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment..."
    & $pythonPath -m venv $venvPath
} else {
    Write-Host "Virtual environment already exists at $venvPath"
}

# Install dependencies if requirements.txt exists
if (Test-Path "$yxobExtractPath\requirements.txt") {
    Write-Host "Installing dependencies from requirements.txt into virtual environment..."
    & $venvPythonPath -m pip install -r "$yxobExtractPath\requirements.txt"
} else {
    Write-Warning "requirements.txt not found. Skipping dependency install."
}

# Get the absolute path of the current working directory
$currentDir = Get-Location

Write-Host "Creating desktop shortcut..."

# Create WScript Shell COM object
$wshShell = New-Object -ComObject WScript.Shell
$shortcut = $wshShell.CreateShortcut($shortcutPath)

# Set the target of the shortcut to use venv Python
$shortcut.TargetPath = $venvPythonPath
$shortcut.Arguments = "`"$currentDir\main.py`""
$shortcut.WorkingDirectory = $currentDir.Path  # Set working directory to current location
$shortcut.IconLocation = "$venvPythonPath,0" # Optional: set Python icon for the shortcut
$shortcut.Save()

# Create a second desktop shortcut for running without a console
$shortcutNameNoConsole = "Yxob (No console).lnk"
$shortcutPathNoConsole = Join-Path -Path $desktopPath -ChildPath $shortcutNameNoConsole

Write-Host "Creating 'Yxob (No console)' desktop shortcut..."

$shortcutNoConsole = $wshShell.CreateShortcut($shortcutPathNoConsole)
$shortcutNoConsole.TargetPath = $venvPythonwPath
$shortcutNoConsole.Arguments = "`"$currentDir\main.py`""
$shortcutNoConsole.WorkingDirectory = $currentDir.Path
$shortcutNoConsole.IconLocation = "$venvPythonwPath,0"
$shortcutNoConsole.Save()

Write-Host "Desktop shortcuts created successfully at $shortcutPath"

# Run yxob with visible console (using venv python) after prompt
if (Test-Path "$yxobExtractPath\main.py") {
    Write-Host "Launching Yxob in console mode..."
    Start-Process -FilePath $venvPythonPath -ArgumentList "$currentDir\main.py" -WindowStyle Normal
    Write-Host "You can safely close this window."
} else {
    Write-Warning "Could not find main.py in the current directory."
}