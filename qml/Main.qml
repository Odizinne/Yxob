import QtQuick 
import QtQuick.Window 
import QtQuick.Controls.FluentWinUI3
import QtQuick.Layouts 

ApplicationWindow {
    id: window
    width: 360
    height: 520
    visible: true
    title: "Yxob"
    
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
    
    header: Rectangle {
        Layout.fillWidth: true
        height: 50
        color: "#1e1e1e"
        border.color: "#333"
        border.width: 1
        
        RowLayout {
            anchors.centerIn: parent
            spacing: 15
            
            Rectangle {
                width: 8
                height: 8
                color: recorder && recorder.isRecording ? "#d13438" : "#666"
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
                color: recorder && recorder.isRecording ? "#ffffff" : "#666"
            }
        }
    }
        
    footer: Rectangle {
        Layout.fillWidth: true
        height: 30
        color: {
            if (recorder && recorder.isRecording) {
                return "#d13438" 
            } else if (recorder && recorder.botConnected) {
                return "#107c10" 
            } else {
                return "#ff8c00" 
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
                    running: recorder ? recorder.isRecording : false
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.3; duration: 500 }
                    NumberAnimation { to: 1.0; duration: 500 }
                }
            }
            
            Label {
                text: {
                    if (recorder && recorder.isRecording) {
                        return "Recording..."
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
        
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 10
            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Button {
                    Layout.fillWidth: true
                    text: "Server selection"
                    enabled: recorder ? (recorder.botConnected && !recorder.isRecording) : false
                    onClicked: discordDialog.open()
                }

                Button {
                    Layout.fillWidth: true
                    text: "User Exclusions"
                    enabled: recorder ? (recorder.botConnected && !recorder.isRecording) : false
                    onClicked: userExclusionDialog.show()
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignHCenter
                spacing: 10
                
                Button {
                    Layout.fillWidth: true
                    text: "Start Recording"
                    icon.source: "icons/record.png"
                    enabled: recorder ? (recorder.botConnected && !recorder.isRecording) : false
                    onClicked: {
                        if (recorder) {
                            recorder.startRecording()
                            recordingSeconds = 0
                            recordingTime = "00:00"
                            recordingTimer.start()
                        }
                    }
                }
                
                Button {
                    Layout.fillWidth: true
                    text: "Stop Recording"
                    icon.source: "icons/stop.png"
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
            }
        }
        
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#2b2b2b"
            radius: 5
            
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
                        anchors.margins: 10

                        // Green dot - always visible on the left
                        //Rectangle {
                        //    width: 8
                        //    height: 8
                        //    color: "#4CAF50"
                        //    radius: 4
                        //    Layout.alignment: Qt.AlignVCenter
                        //}

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
                                    color: "#4CAF50"
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

                                    // Smooth transition to 2px when not speaking
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
                                    color: "#66BB6A"
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

                                    // Smooth transition to 2px when not speaking
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
                                    color: "#81C784"
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

                                    // Smooth transition to 2px when not speaking
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
                            color: "#ffffff"
                        }

                        // Audio bars container - on the right, always visible


                        Label {
                            text: "Recording"
                            color: "#666"
                            font.pixelSize: 12
                        }
                    }
                }
                
                Label {
                    anchors.centerIn: parent
                    text: "No users being recorded"
                    color: "#999"
                    visible: usersList.count === 0
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 10
            
            Button {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignHCenter
                text: "Transcript Recordings"
                icon.source: "icons/transcript.png"
                enabled: recorder ? (recorder.botConnected && !recorder.isRecording) : false
                onClicked: {
                    transcriptDialog.show()
                }
            }
        }
    }

    UserExclusionDialog {
        id: userExclusionDialog
    }

    Dialog {
        anchors.centerIn: parent
        width: 320
        id: discordDialog
        modal: true
        title: "Channel selection"
        GridLayout {
            anchors.fill: parent
            rowSpacing: 12
            columnSpacing: 12
            columns: 2
            
            Label {
                text: "Server"
                font.pixelSize: 14
                font.bold: true
            }

            ComboBox {
                id: guildsCombo
                Layout.fillWidth: true
                textRole: "name"
                model: recorder ? recorder.guildsModel : null
                enabled: recorder ? (recorder.botConnected && !recorder.isRecording) : false
                currentIndex: recorder ? recorder.selectedGuildIndex : -1
                
                onActivated: {
                    if (recorder && currentIndex !== recorder.selectedGuildIndex) {
                        recorder.setSelectedGuild(currentIndex)
                    }
                }
                
                Connections {
                    target: recorder
                    function onGuildsUpdated() {
                        if (recorder && recorder.selectedGuildIndex >= 0) {
                            guildsCombo.currentIndex = recorder.selectedGuildIndex
                        }
                    }
                }
                
                delegate: ItemDelegate {
                    width: guildsCombo.width
                    text: name
                    highlighted: guildsCombo.highlightedIndex === index
                }
            }
            
            Label {
                text: "Channel"
                font.pixelSize: 14
                font.bold: true
            }
            
            ComboBox {
                id: channelsCombo
                Layout.fillWidth: true
                textRole: "name"
                model: recorder ? recorder.channelsModel : null
                enabled: recorder ? (recorder.botConnected && !recorder.isRecording) : false
                
                currentIndex: recorder ? recorder.selectedChannelIndex : -1
                
                onActivated: {
                    if (recorder && currentIndex !== recorder.selectedChannelIndex) {
                        recorder.setSelectedChannel(currentIndex)
                    }
                }
                
                Connections {
                    target: recorder
                    function onChannelsUpdated() {
                        if (recorder && recorder.selectedChannelIndex >= 0) {
                            channelsCombo.currentIndex = recorder.selectedChannelIndex
                        }
                    }
                }
                
                delegate: ItemDelegate {
                    width: channelsCombo.width
                    highlighted: channelsCombo.highlightedIndex === index
                    
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 10
                        
                        Label {
                            text: name
                            Layout.fillWidth: true
                            font.pixelSize: 14
                        }
                        
                        Rectangle {
                            Layout.preferredWidth: 25
                            Layout.preferredHeight: 18
                            color: memberCount > 0 ? "#4CAF50" : "#666"
                            radius: 9
                            
                            Label {
                                anchors.centerIn: parent
                                text: memberCount
                                font.pixelSize: 10
                                color: "white"
                                font.bold: true
                            }
                        }
                    }
                }
                
                displayText: currentIndex >= 0 ? currentText + " (" + 
                           (model && model.data ? model.data(model.index(currentIndex, 0), Qt.UserRole + 1) : "0") + 
                           " members)" : "Select channel..."
            }

            Item {}
            Button {
                Layout.fillWidth: true
                text: recorder && recorder.isJoined ? "Leave Channel" : "Join Channel"
                enabled: recorder ? (recorder.botConnected && !recorder.isRecording) : false
                onClicked: {
                    if (recorder) {
                        if (recorder.isJoined) {
                            recorder.leaveChannel()
                        } else {
                            recorder.joinChannel()
                        }
                    }
                }
            }
        }
    }
}
