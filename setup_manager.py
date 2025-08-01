import os
import platform
import subprocess
import threading
import asyncio
import requests
from PySide6.QtCore import QObject, Signal, Slot, Property, QStandardPaths, QSettings

class SetupManager(QObject):
    # Define the signals
    setupCompleted = Signal(str)  # Emitted when setup is complete with token
    ffmpegInstallInProgressSignal = Signal(bool)
    ffmpegInstalledSignal = Signal(bool)
    ffmpegInstallMessageSignal = Signal(str)
    tokenValidationStatusChanged = Signal(str)
    inviteLinkChanged = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.config_dir = self.get_config_dir()
        self.token_file = os.path.join(self.config_dir, "token.txt")
        self._ffmpeg_install_in_progress = False
        self._ffmpeg_installed = self.check_ffmpeg_installed()
        self._ffmpeg_install_message = ""
        self._os_type = platform.system()
        self._linux_distro = self.get_linux_distro() if self._os_type == "Linux" else ""
        self._token_validation_status = "Not Validated"
        self._client_id = ""
        self._invite_link = ""
        
    def get_config_dir(self):
        """Get platform-specific config directory using Qt's standard paths"""
        config_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        
        # Create directory if it doesn't exist
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
            
        return config_dir

    @Property(str, notify=inviteLinkChanged)
    def inviteLink(self):
        return self._invite_link
        
    @Property(str, notify=tokenValidationStatusChanged)
    def tokenValidationStatus(self):
        return self._token_validation_status
    
    @Property(str, constant=True)
    def osType(self):
        return self._os_type
        
    @Property(str, constant=True)
    def linuxDistro(self):
        return self._linux_distro
    
    @Property(bool, notify=ffmpegInstallInProgressSignal)
    def ffmpegInstallInProgress(self):
        return self._ffmpeg_install_in_progress
        
    @tokenValidationStatus.setter
    def tokenValidationStatus(self, value):
        if self._token_validation_status != value:
            self._token_validation_status = value
            self.tokenValidationStatusChanged.emit(value)

    @ffmpegInstallInProgress.setter
    def ffmpegInstallInProgress(self, value):
        if self._ffmpeg_install_in_progress != value:
            self._ffmpeg_install_in_progress = value
            self.ffmpegInstallInProgressSignal.emit(value)
    
    @Property(bool, notify=ffmpegInstalledSignal)
    def ffmpegInstalled(self):
        return self._ffmpeg_installed
        
    @ffmpegInstalled.setter
    def ffmpegInstalled(self, value):
        if self._ffmpeg_installed != value:
            self._ffmpeg_installed = value
            self.ffmpegInstalledSignal.emit(value)
            
    @Property(str, notify=ffmpegInstallMessageSignal)
    def ffmpegInstallMessage(self):
        return self._ffmpeg_install_message
        
    @ffmpegInstallMessage.setter
    def ffmpegInstallMessage(self, value):
        if self._ffmpeg_install_message != value:
            self._ffmpeg_install_message = value
            self.ffmpegInstallMessageSignal.emit(value)
    
    def get_linux_distro(self):
        """Try to determine Linux distribution"""
        try:
            # Check for os-release file
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release", "r") as f:
                    for line in f:
                        if line.startswith("ID="):
                            distro = line.split("=")[1].strip().strip('"').strip("'").lower()
                            if "ubuntu" in distro:
                                return "Ubuntu"
                            elif "debian" in distro:
                                return "Debian"
                            elif "fedora" in distro:
                                return "Fedora"
                            elif "arch" in distro:
                                return "Arch"
            
            # Check for specific files
            if os.path.exists("/etc/debian_version"):
                return "Debian"
            elif os.path.exists("/etc/fedora-release"):
                return "Fedora"
            elif os.path.exists("/etc/arch-release"):
                return "Arch"
        except:
            pass
        
        return "Unknown"
    
    def check_ffmpeg_installed(self):
        """Check if FFmpeg is installed"""
        try:
            # Try to run ffmpeg -version
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return True
        except:
            return False

    @Slot(str)
    def validate_token(self, token):
        """Validate the bot token and generate the invite link."""
        if not token or token.strip() == "":
            self.tokenValidationStatus = "Invalid Token"
            return

        # Run validation in a separate thread to avoid blocking UI
        import threading
        threading.Thread(target=self._validate_token_async, args=(token,), daemon=True).start()

    def _validate_token_async(self, token):
        """Validate token in a separate thread"""
        try:
            # Fetch client ID from Discord API
            url = "https://discord.com/api/v10/users/@me"
            headers = {"Authorization": f"Bot {token}"}
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                self._client_id = data.get("id")
                self.tokenValidationStatus = "Validated"

                # Permissions: Connect (0x100000), Use Voice Activity (0x2000000)
                permissions = 34603008  # Basic bot permissions + voice permissions
                self._invite_link = f"https://discord.com/api/oauth2/authorize?client_id={self._client_id}&permissions={permissions}&scope=bot"
                self.inviteLinkChanged.emit(self._invite_link)
            elif response.status_code == 401:
                self.tokenValidationStatus = "Invalid Token"
            else:
                self.tokenValidationStatus = f"Error: HTTP {response.status_code}"
        except requests.exceptions.Timeout:
            self.tokenValidationStatus = "Error: Request timeout"
        except requests.exceptions.ConnectionError:
            self.tokenValidationStatus = "Error: Connection failed"
        except Exception as e:
            self.tokenValidationStatus = f"Error: {str(e)}"

    @Slot()
    def installFFmpegWindows(self):
        """Install FFmpeg on Windows"""
        if self._ffmpeg_installed or self._ffmpeg_install_in_progress:
            return
            
        self.ffmpegInstallInProgress = True
        self.ffmpegInstallMessage = "Starting download..."
        
        # Run the installation in a separate thread
        threading.Thread(target=self._install_ffmpeg_windows, daemon=True).start()
    
    def _install_ffmpeg_windows(self):
        """Download and install FFmpeg for Windows"""
        import tempfile
        import zipfile
        import urllib.request
        import shutil
        import ctypes
        import sys
        
        ffmpeg_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        
        try:
            # Create temp directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download file
                self.ffmpegInstallMessage = "Downloading FFmpeg..."
                zip_path = os.path.join(temp_dir, "ffmpeg.zip")
                urllib.request.urlretrieve(ffmpeg_url, zip_path)
                
                # Extract zip
                self.ffmpegInstallMessage = "Extracting files..."
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Find bin directory
                bin_dir = None
                for root, dirs, files in os.walk(temp_dir):
                    if "bin" in dirs:
                        bin_dir = os.path.join(root, "bin")
                        break
                
                if not bin_dir:
                    raise Exception("Could not find bin directory in downloaded files")
                
                # Determine install location
                python_dir = os.path.dirname(sys.executable)
                is_admin = ctypes.windll.shell32.IsUserAnAdmin() if hasattr(ctypes.windll, 'shell32') else False
                
                # Check if directory is writable
                is_writable = os.access(python_dir, os.W_OK)
                
                if not is_writable and not is_admin:
                    self.ffmpegInstallMessage = "Python directory is not writable. Installing to user directory..."
                    install_dir = os.path.join(os.path.expanduser("~"), "ffmpeg", "bin")
                    os.makedirs(install_dir, exist_ok=True)
                else:
                    install_dir = python_dir
                
                # Copy files
                self.ffmpegInstallMessage = f"Installing FFmpeg to {install_dir}..."
                for file in os.listdir(bin_dir):
                    if file.endswith(".exe"):
                        shutil.copy2(os.path.join(bin_dir, file), os.path.join(install_dir, file))
                
                # Add to PATH if needed
                if install_dir != python_dir:
                    # Get current PATH
                    path = os.environ.get("PATH", "")
                    
                    # Check if already in PATH
                    if install_dir not in path:
                        # Add to user PATH
                        self.ffmpegInstallMessage = "Adding FFmpeg to user PATH..."
                        subprocess.run(
                            f'setx PATH "{install_dir};{path}"',
                            shell=True, 
                            check=True
                        )
                
                self.ffmpegInstallMessage = "FFmpeg installed successfully!"
                self.ffmpegInstalled = True
        
        except Exception as e:
            self.ffmpegInstallMessage = f"Installation failed: {str(e)}"
            print(f"FFmpeg installation error: {e}")
        finally:
            self.ffmpegInstallInProgress = False

    def is_setup_complete(self):
        """Check if both token is set up and FFmpeg is installed"""
        self.ffmpegInstalled = self.check_ffmpeg_installed()

        token_valid = False
        if os.path.exists(self.token_file):
            with open(self.token_file, "r") as f:
                token = f.read().strip()
                token_valid = token != "" and not token.startswith("REPLACE_THIS")

        return token_valid and self.ffmpegInstalled
    
    @Slot(str)
    def save_token(self, token):
        """Save bot token to file and signal completion"""
        with open(self.token_file, "w") as f:
            f.write(token)
        
        self.setupCompleted.emit(token)
    
    @Slot(result=str)
    def get_token(self):
        """Get the saved token"""
        if not os.path.exists(self.token_file):
            return ""
            
        with open(self.token_file, "r") as f:
            token = f.read().strip()
            if token == "" or token.startswith("REPLACE_THIS"):
                return ""
            return token

    # User exclusion methods
    @Slot(result=str)
    def get_excluded_users(self):
        """Get the excluded users list"""
        settings = QSettings()
        return settings.value("excludedUsers", "")

    @Slot(str)
    def set_excluded_users(self, excluded_users):
        """Set the excluded users list"""
        settings = QSettings()
        settings.setValue("excludedUsers", excluded_users)
        settings.sync()

    def get_excluded_users_list(self):
        """Get excluded users as a list"""
        excluded_users_str = self.get_excluded_users()
        if not excluded_users_str.strip():
            return []
        
        # Split by comma and clean up whitespace
        excluded_users = [user.strip().lower() for user in excluded_users_str.split(",")]
        return [user for user in excluded_users if user]  # Remove empty strings