import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Material
import "."

ApplicationWindow {
    id: setupWindow
    visible: true
    width: 500
    height: lyt.implicitHeight + 80
    minimumWidth: 500
    minimumHeight: lyt.implicitHeight + 80
    title: "Yxob Setup"
    Material.theme: YxobSettings.darkMode ? Material.Dark : Material.Light
    Material.accent: Colors.accentColor
    Material.primary: Colors.primaryColor
    color: Colors.backgroundColor
    
    property bool tokenValid: tokenInput.text.trim() !== ""
    property bool readyToGo: tokenValid && setupManager.ffmpegInstalled && setupManager.tokenValidationStatus === "Validated"
    
    signal setupFinished(string token)
    
    // Load existing token when component is completed
    Component.onCompleted: {
        if (setupManager) {
            let existingToken = setupManager.get_token()
            if (existingToken && existingToken !== "") {
                tokenInput.text = existingToken
                // Auto-validate the existing token
                setupManager.validate_token(existingToken)
            }
        }
    }
    
    header: ToolBar {
        height: 50
        Material.elevation: 6
        
        Label {
            anchors.centerIn: parent
            text: "Yxob Setup"
            font.pixelSize: 16
            font.bold: true
        }
    }
    
    ColumnLayout {
        id: lyt
        anchors.fill: parent
        anchors.margins: 20
        spacing: 25
        
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 15
            
            Label {
                text: "Create Discord Application"
                Layout.leftMargin: 10
                color: Material.accent
                font.bold: true
            }
            
            Pane {
                Layout.fillWidth: true
                Material.background: Colors.paneColor
                Material.elevation: 6
                Material.roundedScale: Material.ExtraSmallScale
                
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 12
                    
                    Button {
                        text: "Open Discord Developer Portal"
                        highlighted: true
                        Layout.alignment: Qt.AlignLeft
                        onClicked: Qt.openUrlExternally("https://discord.com/developers/applications")
                    }
                    
                    Label {
                        text: "• Create a new application and name it 'Yxob'"
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                    }
                    
                    Label {
                        text: "• Go to the Bot tab"
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                    }
                    
                    Label {
                        text: "• Enable 'Server Members Intent'"
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                    }
                    
                    Label {
                        text: "• Click 'Reset Token' and copy it"
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
        
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 15
            
            Label {
                text: "Bot Token Setup"
                Layout.leftMargin: 10
                color: Material.accent
                font.bold: true
            }
            
            Pane {
                Layout.fillWidth: true
                Material.background: Colors.paneColor
                Material.elevation: 6
                Material.roundedScale: Material.ExtraSmallScale
                
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 12
                    
                    Label {
                        text: "⚠️ Never share your bot token with anyone"
                        color: "#ff8c00"
                    }
                    
                    TextField {
                        id: tokenInput
                        Layout.fillWidth: true
                        placeholderText: "Paste your bot token here"
                        echoMode: TextInput.Password
                    }
                    
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        
                        Button {
                            text: setupManager && setupManager.tokenValidationStatus === "Validated" ? "✓ Token is valid" : "Validate Token"
                            enabled: setupManager && setupManager.tokenValidationStatus !== "Validated" && tokenInput.text.trim() !== ""
                            onClicked: {
                                setupManager.validate_token(tokenInput.text.trim())
                            }
                        }
                        
                        Button {
                            text: "Invite Yxob to your server"
                            enabled: setupManager && setupManager.tokenValidationStatus === "Validated"
                            highlighted: enabled
                            onClicked: {
                                Qt.openUrlExternally(setupManager.inviteLink)
                            }
                        }
                    }
                }
            }
        }
        
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 15
            
            Label {
                text: "Install FFmpeg"
                Layout.leftMargin: 10
                color: Material.accent
                font.bold: true
            }
            
            Pane {
                Layout.fillWidth: true
                Material.background: Colors.paneColor
                Material.elevation: 6
                Material.roundedScale: Material.ExtraSmallScale
                
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 12
                    
                    Label {
                        text: "FFmpeg is required for Yxob to process audio recordings."
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                    }
                    
                    Button {
                        text: setupManager && setupManager.ffmpegInstalled ? "✓ FFmpeg is installed" : "Install FFmpeg"
                        Layout.alignment: Qt.AlignLeft
                        onClicked: ffmpegDialog.open()
                        enabled: setupManager && !setupManager.ffmpegInstalled
                    }
                }
            }
        }
        
        Button {
            text: "Start Yxob"
            Layout.alignment: Qt.AlignRight
            Layout.preferredWidth: 150
            enabled: readyToGo
            highlighted: true
            
            onClicked: {
                setupManager.save_token(tokenInput.text.trim())
                setupFinished(tokenInput.text.trim())
                setupWindow.close()
            }
        }
    }
    
    Dialog {
        id: ffmpegDialog
        anchors.centerIn: parent
        width: Math.min(600, setupWindow.width - 40)
        title: "FFmpeg Installation"
        standardButtons: Dialog.Close
        
        onClosed: {
            // Refresh FFmpeg status when dialog closes (in case user manually installed it)
            if (setupManager) {
                setupManager.ffmpegInstalled = setupManager.check_ffmpeg_installed()
            }
        }
        
        ColumnLayout {
            anchors.fill: parent
            spacing: 15
            
            Label {
                text: "FFmpeg is required for Yxob to process audio files."
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
            
            // Windows instructions
            ColumnLayout {
                visible: setupManager && setupManager.osType === "Windows"
                Layout.fillWidth: true
                spacing: 10
                
                Label {
                    text: "For Windows:"
                    font.bold: true
                }
                
                Label {
                    text: "FFmpeg can be automatically downloaded and installed for you."
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                }
                
                RowLayout {
                    Layout.fillWidth: true
                    
                    Button {
                        highlighted: true
                        text: setupManager && setupManager.ffmpegInstallInProgress ? "Installing..." :
                              setupManager && setupManager.ffmpegInstalled ? "Installation Complete" : "Install FFmpeg"
                        enabled: setupManager && !setupManager.ffmpegInstallInProgress && !setupManager.ffmpegInstalled
                        Layout.alignment: Qt.AlignLeft
                        onClicked: setupManager.installFFmpegWindows()
                    }
                    
                    ProgressBar {
                        visible: setupManager && setupManager.ffmpegInstallInProgress
                        Layout.fillWidth: true
                        indeterminate: true
                    }
                }
                
                Label {
                    visible: setupManager && setupManager.ffmpegInstalled
                    text: "✓ FFmpeg has been installed successfully!"
                    color: Material.accent
                }
                
                Label {
                    visible: setupManager && setupManager.ffmpegInstallMessage !== ""
                    text: setupManager ? setupManager.ffmpegInstallMessage : ""
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    color: Material.hintTextColor
                }
            }
            
            // Linux instructions
            ColumnLayout {
                visible: setupManager && setupManager.osType === "Linux"
                Layout.fillWidth: true
                spacing: 10
                
                Label {
                    text: "For Linux:"
                    font.bold: true
                }
                
                Label {
                    text: "Please run the following command in your terminal:"
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                }
                
                Rectangle {
                    Layout.fillWidth: true
                    height: linuxCommand.height + 20
                    color: Material.foreground
                    opacity: 0.1
                    radius: 5
                    
                    TextEdit {
                        id: linuxCommand
                        anchors.centerIn: parent
                        width: parent.width - 20
                        readOnly: true
                        selectByMouse: true
                        wrapMode: Text.Wrap
                        text: {
                            if (!setupManager) return ""
                            if (setupManager.linuxDistro === "Ubuntu" || setupManager.linuxDistro === "Debian")
                                return "sudo apt install ffmpeg"
                            else if (setupManager.linuxDistro === "Fedora")
                                return "sudo dnf install ffmpeg"
                            else if (setupManager.linuxDistro === "Arch")
                                return "sudo pacman -S ffmpeg"
                            else
                                return "# Please install ffmpeg using your distribution's package manager"
                        }
                    }
                }
                
                Button {
                    text: "Copy Command"
                    Layout.alignment: Qt.AlignRight
                    onClicked: {
                        linuxCommand.selectAll()
                        linuxCommand.copy()
                    }
                }
            }
            
            // macOS instructions
            ColumnLayout {
                visible: setupManager && setupManager.osType === "Darwin"
                Layout.fillWidth: true
                spacing: 10
                
                Label {
                    text: "For macOS:"
                    font.bold: true
                }
                
                Label {
                    text: "Please install FFmpeg using Homebrew:"
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                }
                
                Rectangle {
                    Layout.fillWidth: true
                    height: macCommand.height + 20
                    color: Material.foreground
                    opacity: 0.1
                    radius: 5
                    
                    TextEdit {
                        id: macCommand
                        anchors.centerIn: parent
                        width: parent.width - 20
                        readOnly: true
                        selectByMouse: true
                        wrapMode: Text.Wrap
                        text: "brew install ffmpeg"
                    }
                }
                
                Button {
                    text: "Copy Command"
                    Layout.alignment: Qt.AlignRight
                    onClicked: {
                        macCommand.selectAll()
                        macCommand.copy()
                    }
                }
                
                Label {
                    text: "If you don't have Homebrew installed, install it first with:"
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                }
                
                Rectangle {
                    Layout.fillWidth: true
                    height: brewCommand.height + 20
                    color: Material.foreground
                    opacity: 0.1
                    radius: 5
                    
                    TextEdit {
                        id: brewCommand
                        anchors.centerIn: parent
                        width: parent.width - 20
                        readOnly: true
                        selectByMouse: true
                        wrapMode: Text.Wrap
                        text: '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
                    }
                }
                
                Button {
                    text: "Copy Command"
                    Layout.alignment: Qt.AlignRight
                    onClicked: {
                        brewCommand.selectAll()
                        brewCommand.copy()
                    }
                }
            }
        }
    }
}