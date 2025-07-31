import QtQuick
import QtQuick.Window
import QtQuick.Controls.FluentWinUI3
import QtQuick.Layouts
import QtCore

ApplicationWindow {
    id: exclusionDialog
    title: "User Exclusion List"
    width: 500
    height: minimumHeight
    minimumWidth: 400
    minimumHeight: mainLyt.implicitHeight + 40
    flags: Qt.Dialog
    modality: Qt.ApplicationModal
    
    Settings {
        id: settings
        property string excludedUsers: ""
    }
    
    property string currentExcludedUsers: settings.excludedUsers
    
    ColumnLayout {
        id: mainLyt
        anchors.fill: parent
        anchors.margins: 20
        spacing: 15
        
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 10
            
            Label {
                text: "Excluded Users"
                font.pixelSize: 16
                font.bold: true
            }
            
            Label {
                text: "Enter usernames separated by commas. These users will not be recorded."
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                font.pixelSize: 12
                opacity: 0.8
            }
            
            Label {
                text: "Example: user1, user2, user3"
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                opacity: 0.5
                font.pixelSize: 11
                font.italic: true
            }
        }
                
        TextField {
            Layout.fillWidth: true
            id: excludedUsersInput
            text: currentExcludedUsers
            placeholderText: "Enter usernames separated by commas..."
            //wrapMode: TextArea.Wrap
            selectByMouse: true
            color: "#ffffff"
            placeholderTextColor: "#999"
        }
            
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            
            Button {
                text: "Clear All"
                onClicked: {
                    excludedUsersInput.text = ""
                }
            }
            
            Item { Layout.fillWidth: true }
            
            Button {
                text: "Cancel"
                onClicked: {
                    excludedUsersInput.text = currentExcludedUsers
                    exclusionDialog.close()
                }
            }
            
            Button {
                text: "Save"
                highlighted: true
                onClicked: {
                    settings.excludedUsers = excludedUsersInput.text.trim()
                    currentExcludedUsers = settings.excludedUsers
                    
                    // Notify the recorder about the change
                    if (recorder) {
                        recorder.updateExcludedUsers(settings.excludedUsers)
                    }
                    
                    exclusionDialog.close()
                }
            }
        }
    }
    
    // Load current settings when dialog opens
    onVisibleChanged: {
        if (visible) {
            excludedUsersInput.text = currentExcludedUsers
        }
    }
}