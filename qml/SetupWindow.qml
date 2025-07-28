import QtQuick
import QtQuick.Window
import QtQuick.Controls.FluentWinUI3
import QtQuick.Layouts

ApplicationWindow {
    id: setupWindow
    visible: true
    width: 500
    height: minimumHeight
    minimumWidth: 500
    minimumHeight: mainLyt.implicitHeight + 40 + 50
    title: "Yxob Setup"
    
    property bool tokenValid: tokenInput.text.trim() !== ""
    property bool readyToGo: tokenValid && setupManager.tokenValidationStatus === "Validated"
    
    signal setupFinished(string token)
    
    header: Rectangle {
        height: 50
        color: "#1e1e1e"
        border.color: "#333"
        border.width: 1
        
        Label {
            anchors.centerIn: parent
            text: "Yxob Setup"
            font.pixelSize: 16
            font.bold: true
            color: "#ffffff"
        }
    }
    
    ColumnLayout {
        id: mainLyt
        anchors.fill: parent
        anchors.margins: 20
        spacing: 25
        
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 15
            
            Label {
                text: "Create Discord Application"
                font.pixelSize: 14
                font.bold: true
                color: "#ffffff"
            }
            
            Rectangle {
                Layout.fillWidth: true
                height: devPortalContent.implicitHeight + 30
                color: "#2b2b2b"
                radius: 8
                border.color: "#444"
                border.width: 1
                
                ColumnLayout {
                    id: devPortalContent
                    anchors.fill: parent
                    anchors.margins: 15
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
                        color: "#cccccc"
                        font.pixelSize: 13
                    }
                    
                    Label {
                        text: "• Go to the Bot tab"
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        color: "#cccccc"
                        font.pixelSize: 13
                    }
                    
                    Label {
                        text: "• Enable 'Server Members Intent'"
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        color: "#cccccc"
                        font.pixelSize: 13
                    }
                    
                    Label {
                        text: "• Click 'Reset Token' and copy it"
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        color: "#cccccc"
                        font.pixelSize: 13
                    }
                }
            }
        }
        
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 15
            
            Label {
                text: "Bot Token Setup"
                font.pixelSize: 14
                font.bold: true
                color: "#ffffff"
            }
            
            Rectangle {
                Layout.fillWidth: true
                height: tokenContent.implicitHeight + 30
                color: "#2b2b2b"
                radius: 8
                border.color: "#444"
                border.width: 1
                
                ColumnLayout {
                    id: tokenContent
                    anchors.fill: parent
                    anchors.margins: 15
                    spacing: 12
                    
                    Label {
                        text: "⚠️ Never share your bot token with anyone"
                        color: "#ff8c00"
                        font.pixelSize: 12
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
                            text:  setupManager && setupManager.tokenValidationStatus === "Validated" ? "✓ Token is valid" : "Validate Token"
                            enabled:  setupManager && setupManager.tokenValidationStatus !== "Validated" && tokenInput.text.trim() !== ""
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
            
            onClicked: {
                setupManager.save_token(tokenInput.text.trim())
                setupFinished(tokenInput.text.trim())
                setupWindow.close()
            }
        }
    }
}