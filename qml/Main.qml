import QtQuick 
import QtQuick.Layouts
import QtQuick.Controls.Material
import "."

ApplicationWindow {
    id: window
    width: 360
    height: 520
    visible: true
    title: "Yxob"
    Material.theme: YxobSettings.darkMode ? Material.Dark : Material.Light
    Material.accent: Colors.accentColor
    Material.primary: Colors.primaryColor
    color: Colors.backgroundColor
    
    property int recordingSeconds: 0
    property string recordingTime: "00:00"

    Timer {
        id: recordingTimer
        interval: 1000
        repeat: true
        onTriggered: {
            recordingSeconds++
            let minutes = Math.floor(recordingSeconds / 60)
            let seconds = recordingSeconds % 60
            let hours = Math.floor(minutes / 60)
            minutes = minutes % 60
            
            if (hours > 0) {
                recordingTime = String(hours).padStart(2, '0') + ":" + 
                               String(minutes).padStart(2, '0') + ":" + 
                               String(seconds).padStart(2, '0')
            } else {
                recordingTime = String(minutes).padStart(2, '0') + ":" + 
                               String(seconds).padStart(2, '0')
            }
        }
    }
    
    TranscriptDialog {
        id: transcriptDialog
    }

    ConfigurationWindow {
        id: configurationWindow
        visible: false
        function show() {
            if (!visible) {
                x = window.x + 50
                y = window.y + 50
                visible = true
            }
        }
    }

    Shortcut {
        sequence: "Ctrl+Q"
        enabled: true
        onActivated: Qt.quit()
    }
    
    header: ToolBar {
        height: 40
        Material.elevation: 6
        
        RowLayout {
            anchors.fill: parent
            spacing: 0
            property int buttonWidth: Math.max(menuButton.implicitWidth, serversToolButton.implicitWidth)

            ToolButton {
                id: menuButton
                height: parent.height
                text: "File"
                Material.foreground: "white"
                Layout.preferredWidth: parent.buttonWidth
                Layout.preferredHeight: implicitHeight - 4
                onClicked: mainMenu.visible = !mainMenu.visible
                Menu {
                    id: mainMenu
                    topMargin: 40
                    title: qsTr("File")
                    width: 200
                    visible: false

                    MenuItem {
                        text: "Settings"
                        onTriggered: configurationWindow.show()
                    }

                    MenuSeparator {}

                    MenuItem {
                        onTriggered: Qt.quit()

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 16
                            anchors.rightMargin: 16
                            Label {
                                text: "Exit"
                                Layout.fillWidth: true
                            }

                            Label {
                                text: "Ctrl + Q"
                                opacity: 0.4
                                font.pixelSize: 12
                            }
                        }
                    }
                }
            }

            ToolButton {
                id: recordingsToolButton
                text: "Recordings"
                height: parent.height
                Material.foreground: "white"
                Layout.preferredHeight: implicitHeight - 4
                onClicked: recordingsMenu.visible = !recordingsMenu.visible
                
                Menu {
                    id: recordingsMenu
                    title: qsTr("Recordings")
                    topMargin: 40
                    width: 200
                    visible: false

                    MenuItem {
                        text: "Open Recordings Folder"
                        enabled: recorder ? recorder.botConnected : false
                        onTriggered: {
                            if (recorder) {
                                recorder.openRecordingsFolder()
                            }
                        }
                    }

                    MenuItem {
                        text: "Transcript Recordings"
                        enabled: recorder ? (recorder.botConnected && !recorder.isRecording) : false
                        onTriggered: {
                            transcriptDialog.show()
                        }
                    }
                }
            }

            ToolButton {
                id: serversToolButton
                text: "Servers"
                Material.foreground: "white"
                Layout.preferredWidth: parent.buttonWidth
                Layout.preferredHeight: implicitHeight - 4
                height: parent.height
                enabled: recorder ? recorder.botConnected : false
                property var serverData: ({servers: [], channels: {}})
                property var noServersItem: null

                function refreshServerData() {
                    if (recorder) {
                        serverData = recorder.get_servers_with_channels()
                        serverMenuInstantiator.model = serverData.servers
                    }
                }

                onClicked: {
                    refreshServerData()
                    serversMenu.visible = !serversMenu.visible
                }

                Connections {
                    target: recorder
                    function onBotConnectedChanged() {
                        if (recorder && recorder.botConnected) {
                            serversToolButton.refreshServerData()
                        }
                    }
                    function onGuildsUpdated() {
                        serversToolButton.refreshServerData()
                    }
                }

                Menu {
                    id: serversMenu
                    title: qsTr("Servers")
                    topMargin: 40
                    width: 250
                    visible: false

                    MenuItem {
                        text: "Refresh Server List"
                        onTriggered: serversToolButton.refreshServerData()
                    }

                    MenuItem {
                        text: "Invite Yxob to server"
                        enabled: recorder ? recorder.botConnected : false
                        onTriggered: {
                            if (recorder) {
                                let link = recorder.get_invitation_link()
                                if (link) {
                                    Qt.openUrlExternally(link)
                                }
                            }
                        }
                    }

                    MenuItem {
                        text: "Disconnect"
                        enabled: recorder ? recorder.isJoined : false
                        onTriggered: {
                            if (recorder) {
                                recorder.leaveChannel()
                            }
                            serversMenu.close()
                        }
                    }

                    MenuSeparator {}
                }

                Instantiator {
                    id: serverMenuInstantiator
                    model: serversToolButton.serverData.servers

                    delegate: Menu {
                        id: serverMenu
                        required property int index
                        required property var modelData
                        property var noChannelsItem: null
                        title: modelData.name

                        Instantiator {
                            id: channelInstantiator
                            model: serversToolButton.serverData.channels[modelData.id] || []

                            delegate: MenuItem {
                                required property int index
                                required property var modelData

                                text: modelData.name + " (" + (modelData.member_count || 0) + " members)"

                                onTriggered: {
                                    if (recorder) {
                                        // Find the guild index
                                        let guildIndex = -1
                                        for (let i = 0; i < recorder.guildsModel.rowCount(); i++) {
                                            let guildModelIndex = recorder.guildsModel.index(i, 0)
                                            let guildId = recorder.guildsModel.data(guildModelIndex, Qt.UserRole)
                                            if (guildId === serverMenu.modelData.id) {
                                                guildIndex = i
                                                break
                                            }
                                        }
                                        
                                        if (guildIndex >= 0) {
                                            recorder.setSelectedGuild(guildIndex)
                                            
                                            // Find the channel index
                                            let channelIndex = -1
                                            for (let j = 0; j < recorder.channelsModel.rowCount(); j++) {
                                                let channelModelIndex = recorder.channelsModel.index(j, 0)
                                                let channelId = recorder.channelsModel.data(channelModelIndex, Qt.UserRole)
                                                if (channelId === modelData.id) {
                                                    channelIndex = j
                                                    break
                                                }
                                            }
                                            
                                            if (channelIndex >= 0) {
                                                recorder.setSelectedChannel(channelIndex)
                                                // Auto-join the channel when selected
                                                recorder.joinChannel()
                                            }
                                        }
                                    }
                                    serversMenu.close()
                                }
                            }

                            onObjectAdded: function(index, object) {
                                if (serverMenu.noChannelsItem) {
                                    serverMenu.removeItem(serverMenu.noChannelsItem)
                                    serverMenu.noChannelsItem = null
                                }
                                serverMenu.addItem(object)
                            }

                            onObjectRemoved: function(index, object) {
                                serverMenu.removeItem(object)
                                if (channelInstantiator.count === 0) {
                                    serverMenu.noChannelsItem = Qt.createQmlObject(
                                                'import QtQuick.Controls.Material; MenuItem { text: "No channels available"; enabled: false }',
                                                serverMenu,
                                                "noChannelsPlaceholder"
                                                )
                                    serverMenu.addItem(serverMenu.noChannelsItem)
                                }
                            }

                            Component.onCompleted: {
                                if (count === 0) {
                                    serverMenu.noChannelsItem = Qt.createQmlObject(
                                                'import QtQuick.Controls.Material; MenuItem { text: "No channels available"; enabled: false }',
                                                serverMenu,
                                                "noChannelsPlaceholder"
                                                )
                                    serverMenu.addItem(serverMenu.noChannelsItem)
                                }
                            }
                        }
                    }

                    onObjectAdded: function(index, object) {
                        if (serversToolButton.noServersItem) {
                            serversMenu.removeItem(serversToolButton.noServersItem)
                            serversToolButton.noServersItem = null
                        }
                        serversMenu.insertMenu(index + 4, object)
                    }

                    onObjectRemoved: function(index, object) {
                        serversMenu.removeMenu(object)
                        if (serverMenuInstantiator.count === 0) {
                            serversToolButton.noServersItem = Qt.createQmlObject(
                                        'import QtQuick.Controls.Material; MenuItem { text: "No servers available"; enabled: false }',
                                        serversMenu,
                                        "noServersPlaceholder"
                                        )
                            serversMenu.addItem(serversToolButton.noServersItem)
                        }
                    }

                    Component.onCompleted: {
                        if (count === 0) {
                            serversToolButton.noServersItem = Qt.createQmlObject(
                                        'import QtQuick.Controls.Material; MenuItem { text: "No servers available"; enabled: false }',
                                        serversMenu,
                                        "noServersPlaceholder"
                                        )
                            serversMenu.addItem(serversToolButton.noServersItem)
                        }
                    }
                }
            }

            Item {
                Layout.fillWidth: true
            }

            // Recording time display
            RowLayout {
                spacing: 15
                
                Rectangle {
                    width: 8
                    height: 8
                    color: recorder && recorder.isRecording ? "#d13438" : Material.hintTextColor
                    radius: 4
                    visible: recorder ? recorder.isRecording : false
                    
                    SequentialAnimation on opacity {
                        running: recorder ? recorder.isRecording : false
                        loops: Animation.Infinite
                        NumberAnimation { to: 0.3; duration: 800 }
                        NumberAnimation { to: 1.0; duration: 800 }
                    }
                }
                
                Label {
                    text: recordingTime
                    font.pixelSize: 20
                    font.bold: true
                    font.family: "Consolas, Monaco, monospace"
                    Material.foreground: "white"
                    opacity: recorder && recorder.isRecording ? 1 : 0.5
                }
            }

            Item {
                width: 10
            }
        }
    }
        
    footer: ToolBar {
        height: 30
        Material.background: {
            if (recorder && recorder.isRecording) {
                if (recorder.isPaused) {
                    return "#ff8c00" // Orange for paused
                } else {
                    return "#d13438" // Red for recording
                }
            } else if (recorder && recorder.botConnected) {
                return "#107c10" // Green for connected
            } else {
                return "#ff8c00" // Orange for connecting
            }
        }

        RowLayout {
            anchors.centerIn: parent
            spacing: 10

            Rectangle {
                width: 10
                height: 10
                color: "white"
                radius: 5
                visible: recorder ? recorder.isRecording : false

                SequentialAnimation on opacity {
                    running: recorder ? (recorder.isRecording && !recorder.isPaused) : false
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.3; duration: 500 }
                    NumberAnimation { to: 1.0; duration: 500 }
                }
            }

            Label {
                text: {
                    if (recorder && recorder.isRecording) {
                        if (recorder.isPaused) {
                            return "Paused"
                        } else {
                            return "Recording..."
                        }
                    } else if (recorder && recorder.botConnected) {
                        return "Connected!"
                    } else {
                        return "Connecting..."
                    }
                }
                font.pixelSize: 14
                color: "white"
                font.bold: recorder ? recorder.isRecording : false
            }
        }
    }
    
    ColumnLayout {
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
                
                RowLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignHCenter
                    spacing: 5
                    
                    Item {
                        Layout.fillWidth: true
                    }

                    RoundButton {
                        id: startBtn
                        icon.source: "icons/record.png"
                        icon.height: 14
                        icon.width: 14
                        enabled: recorder ? (recorder.botConnected && !recorder.isRecording) : false
                        highlighted: true
                        Material.accent: "#eb4b3f"
                        onClicked: {
                            if (recorder) {
                                recorder.startRecording()
                                recordingSeconds = 0
                                recordingTime = "00:00"
                                recordingTimer.start()
                            }
                        }
                    }
                    
                    RoundButton {
                        icon.source: recorder && recorder.isPaused ? "icons/play.png" : "icons/pause.png"
                        icon.height: 14
                        icon.width: 14
                        enabled: recorder ? (recorder.isRecording && !recorder.isTranscribing) : false
                        onClicked: {
                            if (recorder) {
                                if (recorder.isPaused) {
                                    recorder.resumeRecording()
                                    recordingTimer.start()
                                } else {
                                    recorder.pauseRecording()
                                    recordingTimer.stop()
                                }
                            }
                        }
                    }
                    
                    RoundButton {
                        icon.source: "icons/stop.png"
                        icon.height: 14
                        icon.width: 14
                        enabled: recorder ? recorder.isRecording : false
                        onClicked: {
                            if (recorder) {
                                recorder.stopRecording()
                                recordingTimer.stop()
                                recordingSeconds = 0
                                recordingTime = "00:00"
                            }
                        }
                    }

                    Item {
                        Layout.fillWidth: true
                    }
                }
            }
        }
        
        Pane {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Material.background: Colors.paneColor
            Material.elevation: 6
            Material.roundedScale: Material.ExtraSmallScale

            ListView {
                id: usersList
                anchors.fill: parent
                anchors.margins: 10
                model: recorder ? recorder.userModel : null
                spacing: 5
                
                delegate: ItemDelegate {
                    width: usersList.width
                    height: 40

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 5
                        anchors.rightMargin: 10

                        Item {
                            width: 26
                            height: 20
                            Layout.alignment: Qt.AlignVCenter

                            Row {
                                anchors.bottom: parent.bottom
                                anchors.horizontalCenter: parent.horizontalCenter
                                anchors.bottomMargin: 2
                                spacing: 3

                                // Bar 1
                                Rectangle {
                                    width: 4
                                    height: model.speaking ? bar1Height : 2
                                    color: Material.accent
                                    radius: 2
                                    anchors.bottom: parent.bottom

                                    property real bar1Height: 2

                                    SequentialAnimation on bar1Height {
                                        running: model.speaking || false
                                        loops: Animation.Infinite

                                        NumberAnimation {
                                            to: 14
                                            duration: 500
                                            easing.type: Easing.InOutQuad
                                        }
                                        NumberAnimation {
                                            to: 2
                                            duration: 400
                                            easing.type: Easing.InOutQuad
                                        }
                                        NumberAnimation {
                                            to: 16
                                            duration: 550
                                            easing.type: Easing.InOutQuad
                                        }
                                        NumberAnimation {
                                            to: 4
                                            duration: 450
                                            easing.type: Easing.InOutQuad
                                        }
                                    }

                                    Behavior on height {
                                        enabled: !(model.speaking || false)
                                        NumberAnimation {
                                            duration: 300
                                            easing.type: Easing.OutQuad
                                        }
                                    }
                                }

                                // Bar 2
                                Rectangle {
                                    width: 4
                                    height: model.speaking ? bar2Height : 2
                                    color: Qt.lighter(Material.accent, 1.2)
                                    radius: 2
                                    anchors.bottom: parent.bottom

                                    property real bar2Height: 2

                                    SequentialAnimation on bar2Height {
                                        running: model.speaking || false
                                        loops: Animation.Infinite

                                        NumberAnimation {
                                            to: 18
                                            duration: 520
                                            easing.type: Easing.InOutQuad
                                        }
                                        NumberAnimation {
                                            to: 3
                                            duration: 380
                                            easing.type: Easing.InOutQuad
                                        }
                                        NumberAnimation {
                                            to: 15
                                            duration: 480
                                            easing.type: Easing.InOutQuad
                                        }
                                        NumberAnimation {
                                            to: 6
                                            duration: 420
                                            easing.type: Easing.InOutQuad
                                        }
                                    }

                                    Behavior on height {
                                        enabled: !(model.speaking || false)
                                        NumberAnimation {
                                            duration: 350
                                            easing.type: Easing.OutQuad
                                        }
                                    }
                                }

                                // Bar 3
                                Rectangle {
                                    width: 4
                                    height: model.speaking ? bar3Height : 2
                                    color: Qt.lighter(Material.accent, 1.4)
                                    radius: 2
                                    anchors.bottom: parent.bottom

                                    property real bar3Height: 2

                                    SequentialAnimation on bar3Height {
                                        running: model.speaking || false
                                        loops: Animation.Infinite

                                        NumberAnimation {
                                            to: 12
                                            duration: 460
                                            easing.type: Easing.InOutQuad
                                        }
                                        NumberAnimation {
                                            to: 5
                                            duration: 500
                                            easing.type: Easing.InOutQuad
                                        }
                                        NumberAnimation {
                                            to: 17
                                            duration: 440
                                            easing.type: Easing.InOutQuad
                                        }
                                        NumberAnimation {
                                            to: 2
                                            duration: 480
                                            easing.type: Easing.InOutQuad
                                        }
                                    }

                                    Behavior on height {
                                        enabled: !(model.speaking || false)
                                        NumberAnimation {
                                            duration: 400
                                            easing.type: Easing.OutQuad
                                        }
                                    }
                                }
                            }
                        }

                        Label {
                            text: model.name || ""
                            Layout.fillWidth: true
                            font.pixelSize: 14
                        }

                        Label {
                            text: {
                                if (!recorder) return ""
                                if (recorder.isPaused) return "Paused"
                                return "Recording"
                            }
                            color: recorder && recorder.isPaused ? Material.hintTextColor : Material.hintTextColor
                            font.pixelSize: 12
                        }
                    }
                }
                
                Label {
                    anchors.centerIn: parent
                    text: "No users being recorded"
                    color: Material.hintTextColor
                    visible: usersList.count === 0
                }
            }
        }
    }
}