import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Material
import QtCore
import "."

ApplicationWindow {
    id: exclusionDialog
    title: "User Exclusion List"
    width: 500
    height: lyt.implicitHeight + 60
    minimumWidth: 400
    minimumHeight: lyt.implicitHeight + 60
    flags: Qt.Dialog
    modality: Qt.ApplicationModal
    Material.theme: YxobSettings.darkMode ? Material.Dark : Material.Light
    Material.accent: Colors.accentColor
    Material.primary: Colors.primaryColor
    color: Colors.backgroundColor
    
    property string currentExcludedUsers: YxobSettings.excludedUsers
    
    ColumnLayout {
        id: lyt
        anchors.fill: parent
        anchors.margins: 20
        spacing: 15
        
        Pane {
            Layout.fillWidth: true
            Material.background: Colors.paneColor
            Material.elevation: 6
            Material.roundedScale: Material.ExtraSmallScale
            
            ColumnLayout {
                anchors.fill: parent
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
                    color: Material.hintTextColor
                }
                
                Label {
                    text: "Example: user1, user2, user3"
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    color: Material.hintTextColor
                    font.pixelSize: 11
                    font.italic: true
                }
                        
                TextField {
                    Layout.fillWidth: true
                    id: excludedUsersInput
                    text: currentExcludedUsers
                    placeholderText: "Enter usernames separated by commas..."
                    selectByMouse: true
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
                    YxobSettings.excludedUsers = excludedUsersInput.text.trim()
                    currentExcludedUsers = YxobSettings.excludedUsers
                    
                    // Notify the recorder about the change
                    if (recorder) {
                        recorder.updateExcludedUsers(YxobSettings.excludedUsers)
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