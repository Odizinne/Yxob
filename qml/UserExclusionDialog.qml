import QtQuick
import QtQuick.Window
import QtQuick.Controls.FluentWinUI3
import QtQuick.Layouts
import QtCore

ApplicationWindow {
    id: exclusionDialog
    title: "User Exclusion List"
    width: 500
    height: 400
    minimumWidth: 400
    minimumHeight: 300
    flags: Qt.Dialog
    modality: Qt.ApplicationModal
    
    Settings {
        id: settings
        property string excludedUsers: ""
    }
    
    property string currentExcludedUsers: settings.excludedUsers
    
    ColumnLayout {
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
                color: "#ffffff"
            }
            
            Label {
                text: "Enter usernames separated by commas. These users will not be recorded."
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: "#cccccc"
                font.pixelSize: 12
            }
            
            Label {
                text: "Example: user1, user2, user3"
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: "#999999"
                font.pixelSize: 11
                font.italic: true
            }
        }
        
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#2b2b2b"
            radius: 8
            border.color: "#444"
            border.width: 1
            
            ScrollView {
                anchors.fill: parent
                anchors.margins: 10
                
                TextArea {
                    id: excludedUsersInput
                    text: currentExcludedUsers
                    placeholderText: "Enter usernames separated by commas..."
                    wrapMode: TextArea.Wrap
                    selectByMouse: true
                    color: "#ffffff"
                    placeholderTextColor: "#999"
                    
                    background: Rectangle {
                        color: "transparent"
                    }
                }
            }
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