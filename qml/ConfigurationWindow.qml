import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Material
import "."

ApplicationWindow {
    id: configurationWindow
    visible: true
    width: lyt.implicitWidth + 30 + 16
    height: 600
    minimumWidth: lyt.implicitWidth + 30 + 16
    maximumWidth: lyt.implicitWidth + 30 + 16
    minimumHeight: 600
    maximumHeight: 600
    transientParent: null
    Material.theme: YxobSettings.darkMode ? Material.Dark : Material.Light
    Material.accent: Colors.accentColor
    Material.primary: Colors.primaryColor
    color: Colors.backgroundColor
    
    header: ToolBar {
        height: 40
        Material.elevation: 8
        Label {
            anchors.centerIn: parent
            text: "Yxob Settings"
            Material.foreground: "white"
            font.pixelSize: 14
            font.bold: true
        }
    }

    property string currentToken: ""
    property string currentExcludedUsers: ""

    Component.onCompleted: {
        if (setupManager) {
            tokenInput.text = setupManager.get_token()
            currentToken = tokenInput.text
            currentExcludedUsers = setupManager.get_excluded_users()
            excludedUsersInput.text = currentExcludedUsers
        }
    }

    ScrollView {
        id: scrlView
        width: container.width
        height: Math.min(parent.height, container.height)
        contentWidth: container.width
        contentHeight: container.height
        anchors.fill: parent
        ScrollBar.vertical.policy: ScrollBar.AlwaysOn

        Item {
            id: container
            width: lyt.implicitWidth + 30
            height: lyt.implicitHeight + 60
            anchors.fill: parent

            ColumnLayout {
                id: lyt
                anchors.fill: parent
                anchors.margins: 15
                spacing: 20

                Label {
                    text: "UI settings"
                    Layout.bottomMargin: -15
                    Layout.leftMargin: 10
                    color: Material.accent
                }
                
                Pane {
                    Layout.fillWidth: true
                    Material.background: Colors.paneColor
                    Layout.preferredWidth: 450
                    Layout.preferredHeight: implicitHeight + 20
                    Material.elevation: 6
                    Material.roundedScale: Material.ExtraSmallScale
                    
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 15
                        
                        RowLayout {
                            Layout.fillWidth: true
                            Label {
                                text: "Dark mode"
                                Layout.fillWidth: true
                            }
                            
                            Item {
                                Layout.preferredHeight: 24
                                Layout.preferredWidth: 24

                                Image {
                                    id: sunImage
                                    anchors.fill: parent
                                    source: "icons/sun.png"
                                    opacity: !themeSwitch.checked ? 1 : 0
                                    rotation: themeSwitch.checked ? 360 : 0
                                    mipmap: true

                                    Behavior on rotation {
                                        NumberAnimation {
                                            duration: 500
                                            easing.type: Easing.OutQuad
                                        }
                                    }

                                    Behavior on opacity {
                                        NumberAnimation { duration: 500 }
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: themeSwitch.checked = !themeSwitch.checked
                                    }
                                }

                                Image {
                                    anchors.fill: parent
                                    id: moonImage
                                    source: "icons/moon.png"
                                    opacity: themeSwitch.checked ? 1 : 0
                                    rotation: themeSwitch.checked ? 360 : 0
                                    mipmap: true

                                    Behavior on rotation {
                                        NumberAnimation {
                                            duration: 500
                                            easing.type: Easing.OutQuad
                                        }
                                    }

                                    Behavior on opacity {
                                        NumberAnimation { duration: 100 }
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: themeSwitch.checked = !themeSwitch.checked
                                    }
                                }
                            }

                            Switch {
                                id: themeSwitch
                                checked: YxobSettings.darkMode
                                onClicked: YxobSettings.darkMode = checked
                                Layout.rightMargin: -10
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Label {
                                text: "Color"
                                Layout.fillWidth: true
                            }

                            ColumnLayout {
                                spacing: 8

                                RowLayout {
                                    spacing: 8

                                    Repeater {
                                        model: 5

                                        Rectangle {
                                            width: 30
                                            height: 30
                                            radius: 5
                                            color: Colors.colorPairs[index][0] 
                                            border.width: YxobSettings.accentColorIndex === index ? 2 : 0
                                            border.color: YxobSettings.darkMode ? "#FFFFFF" : "#000000"

                                            MouseArea {
                                                anchors.fill: parent
                                                onClicked: YxobSettings.accentColorIndex = index
                                                cursorShape: Qt.PointingHandCursor
                                            }

                                            Behavior on border.width {
                                                NumberAnimation { duration: 100 }
                                            }
                                        }
                                    }
                                }

                                RowLayout {
                                    spacing: 8

                                    Repeater {
                                        model: 5

                                        Rectangle {
                                            width: 30
                                            height: 30
                                            radius: 5

                                            color: Colors.colorPairs[index + 5][0]
                                            border.width: YxobSettings.accentColorIndex === (index + 5) ? 2 : 0
                                            border.color: YxobSettings.darkMode ? "#FFFFFF" : "#000000"

                                            MouseArea {
                                                anchors.fill: parent
                                                onClicked: YxobSettings.accentColorIndex = index + 5
                                                cursorShape: Qt.PointingHandCursor
                                            }

                                            Behavior on border.width {
                                                NumberAnimation { duration: 100 }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                Label {
                    text: "User exclusion"
                    Layout.bottomMargin: -15
                    Layout.leftMargin: 10
                    color: Material.accent
                }
                
                Pane {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 450
                    Layout.preferredHeight: implicitHeight + 20
                    Material.background: Colors.paneColor
                    Material.elevation: 6
                    Material.roundedScale: Material.ExtraSmallScale
                    
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 15
                        
                        Label {
                            text: "Enter usernames separated by commas. These users will not be recorded."
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            font.pixelSize: 12
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
                            id: excludedUsersInput
                            Layout.fillWidth: true
                            placeholderText: "Enter usernames separated by commas..."
                            selectByMouse: true
                            Layout.preferredHeight: 35
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
                                text: "Reset"
                                onClicked: {
                                    excludedUsersInput.text = currentExcludedUsers
                                }
                            }

                            Button {
                                text: "Save"
                                highlighted: true
                                enabled: excludedUsersInput.text !== currentExcludedUsers
                                onClicked: {
                                    if (setupManager) {
                                        setupManager.set_excluded_users(excludedUsersInput.text.trim())
                                        currentExcludedUsers = excludedUsersInput.text.trim()
                                    }
                                    
                                    // Notify the recorder about the change
                                    if (recorder) {
                                        recorder.updateExcludedUsers(excludedUsersInput.text.trim())
                                    }
                                }
                            }
                        }
                    }
                }
                
                Label {
                    text: "Discord bot token"
                    Layout.bottomMargin: -15
                    Layout.leftMargin: 10
                    color: Material.accent
                }
                
                Pane {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 450
                    Layout.preferredHeight: implicitHeight + 20
                    Material.background: Colors.paneColor
                    Material.elevation: 6
                    Material.roundedScale: Material.ExtraSmallScale
                    
                    ColumnLayout {
                        id: tokenLayout
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 15

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 0

                            TextField {
                                id: tokenInput
                                Layout.fillWidth: true
                                placeholderText: "Enter your Discord bot token"
                                echoMode: TextInput.Password
                                selectByMouse: true
                                Layout.preferredHeight: 35
                            }

                            RoundButton {
                                flat: true
                                icon.source: "icons/reveal.png"
                                icon.width: 20
                                icon.height: 20
                                Layout.rightMargin: -10

                                onClicked: {
                                    if (tokenInput.echoMode === TextInput.Password) {
                                        tokenInput.echoMode = TextInput.Normal
                                    } else {
                                        tokenInput.echoMode = TextInput.Password
                                    }
                                }
                            }
                        }

                        Label {
                            text: "⚠️ Never share your bot token with anyone"
                            opacity: 0.7
                            color: Material.foreground
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                        }

                        Button {
                            id: saveButton
                            text: "Save and reconnect"
                            highlighted: true
                            enabled: tokenInput.text.trim() !== "" && tokenInput.text !== configurationWindow.currentToken
                            onClicked: {
                                if (setupManager) {
                                    setupManager.save_token(tokenInput.text.trim())
                                    configurationWindow.currentToken = tokenInput.text.trim()
                                }
                                configurationWindow.close()
                            }
                        }
                    }
                }
            }
        }
    }
}