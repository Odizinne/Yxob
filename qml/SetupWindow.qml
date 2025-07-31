import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Material
import "."

ApplicationWindow {
    id: setupWindow
    visible: true
    width: 500
    height: lyt.implicitHeight + 70
    minimumWidth: 500
    minimumHeight: lyt.implicitHeight + 70
    title: "Yxob Setup"
    Material.theme: YxobSettings.darkMode ? Material.Dark : Material.Light
    Material.accent: Colors.accentColor
    Material.primary: Colors.primaryColor
    color: Colors.backgroundColor
    
    property bool tokenValid: tokenInput.text.trim() !== ""
    property bool readyToGo: tokenValid && setupManager.tokenValidationStatus === "Validated"
    
    signal setupFinished(string token)
    
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
}