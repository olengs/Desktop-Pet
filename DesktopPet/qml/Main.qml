pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Window

Window {
    id: root

    property int petWindowWidth: 250
    property int petWindowHeight: 324
    property int petWidth: 170
    property int petHeight: 194
    property string compactNormalPose: "idle"
    property string compactNormalMood: "idle"
    property string compactSleepPose: "sleep"
    property string compactSleepMood: "idle"
    property string compactDisturbedPose: "annoyed"
    property string compactDisturbedMood: "annoyed"
    property int compactSleepDelayMs: 12000
    property int compactDisturbedDurationMs: 2400

    // Set these to use your own sprite sheet or compact icon art.
    property url petSpriteSheet: ""
    property url petCompactIcon: ""
    property int petSpriteFrameWidth: 0
    property int petSpriteFrameHeight: 0
    property int petSpriteFrameCount: 4
    property int petSpriteFrameDuration: 120

    width: petWindowWidth
    height: petWindowHeight
    visible: false
    color: "transparent"
    title: "Garena Pet"
    flags: Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint

    property string petMood: "idle"
    property color ink: "#18212f"
    property color panel: "#fbfcff"
    property color line: "#d9e2ef"
    property var backend: backendClient
    property var voice: voiceRecorder
    readonly property bool menuOpen: chatWindow.visible || settingsWindow.visible
    readonly property bool controlsVisible: petMouseArea.containsMouse || settingsButton.hovered || chatButton.hovered

    onMenuOpenChanged: {
        if (menuOpen) {
            petMood = "idle"
        }
    }

    Component.onCompleted: {
        addMessage("pet", "I am Mimo. I can chat, remember your demo matches, and listen when you want to talk.")
    }

    ListModel {
        id: chatModel
    }

    function addMessage(sender, text) {
        chatModel.append({ sender: sender, text: text })
        chatWindow.scrollToEnd()
    }

    function pulseMood(mood) {
        petMood = mood && mood.length > 0 ? mood : "thinking"
        resetMoodTimer.restart()
    }

    function sendText(text) {
        const trimmed = text.trim()
        if (trimmed.length === 0) {
            return
        }
        addMessage("user", trimmed)
        pulseMood("thinking")
        root.backend.sendMessage(trimmed)
    }

    function availableScreenWidth() {
        const candidate = Screen.desktopAvailableWidth > 0 ? Screen.desktopAvailableWidth : Screen.width
        return candidate > 0 ? candidate : width
    }

    function availableScreenHeight() {
        const candidate = Screen.desktopAvailableHeight > 0 ? Screen.desktopAvailableHeight : Screen.height
        return candidate > 0 ? candidate : height
    }

    function clampWindowX(candidateX, targetWidth) {
        return Math.max(0, Math.min(candidateX, Math.max(0, availableScreenWidth() - targetWidth)))
    }

    function clampWindowY(candidateY, targetHeight) {
        return Math.max(0, Math.min(candidateY, Math.max(0, availableScreenHeight() - targetHeight)))
    }

    function placeMenuWindow(window, verticalOffset) {
        const gap = 14
        const leftCandidate = root.x - window.width - gap
        const rightCandidate = root.x + root.width + gap
        window.x = leftCandidate >= 0 ? leftCandidate : clampWindowX(rightCandidate, window.width)
        window.y = clampWindowY(root.y + verticalOffset, window.height)
    }

    function toggleChatWindow() {
        if (chatWindow.visible) {
            chatWindow.hide()
            return
        }

        settingsWindow.hide()
        placeMenuWindow(chatWindow, 4)
        chatWindow.show()
        chatWindow.raise()
        chatWindow.requestActivate()
        chatWindow.scrollToEnd()
    }

    function toggleSettingsWindow() {
        if (settingsWindow.visible) {
            settingsWindow.hide()
            return
        }

        chatWindow.hide()
        placeMenuWindow(settingsWindow, 36)
        settingsWindow.refreshFields()
        settingsWindow.show()
        settingsWindow.raise()
        settingsWindow.requestActivate()
    }

    Timer {
        id: resetMoodTimer
        interval: 4200
        repeat: false
        onTriggered: {
            if (root.menuOpen) {
                root.petMood = "idle"
            }
        }
    }

    Connections {
        target: root.backend

        function onReplyReceived(message, mood) {
            root.addMessage("pet", message)
            root.pulseMood(mood)
        }

        function onVoiceTranscriptReceived(transcript) {
            root.addMessage("user", "Voice: " + transcript)
        }

        function onEventAccepted(summary, mood) {
            root.addMessage("memory", summary)
            root.pulseMood(mood)
        }

        function onChatError(message) {
            root.addMessage("memory", message)
            root.pulseMood("annoyed")
        }
    }

    Connections {
        target: root.voice

        function onVoiceError(message) {
            root.addMessage("memory", message)
            root.pulseMood("annoyed")
        }

        function onRecordingChanged() {
            if (root.voice.recording) {
                root.petMood = "thinking"
            }
        }
    }

    PetBehaviorController {
        id: compactBehavior
        compactMode: !root.menuOpen
        normalPose: root.compactNormalPose
        normalMood: root.compactNormalMood
        sleepPose: root.compactSleepPose
        sleepMood: root.compactSleepMood
        disturbedPose: root.compactDisturbedPose
        disturbedMood: root.compactDisturbedMood
        sleepDelayMs: root.compactSleepDelayMs
        disturbedDurationMs: root.compactDisturbedDurationMs
    }

    ChatWindow {
        id: chatWindow
        backend: root.backend
        voice: root.voice
        messageModel: chatModel
        ink: root.ink
        panel: root.panel
        line: root.line
        onSendTextRequested: function(text) {
            root.sendText(text)
        }
    }

    SettingsWindow {
        id: settingsWindow
        backend: root.backend
        voice: root.voice
        ink: root.ink
        panel: root.panel
        line: root.line
    }

    PetSprite {
        id: pet
        z: 1
        width: root.petWidth
        height: root.petHeight
        mood: root.menuOpen ? root.petMood : compactBehavior.mood
        pose: compactBehavior.pose
        compact: true
        idleBounceEnabled: false
        spriteSheetSource: root.petSpriteSheet
        compactIconSource: root.petCompactIcon
        spriteFrameWidth: root.petSpriteFrameWidth
        spriteFrameHeight: root.petSpriteFrameHeight
        spriteFrameCount: root.petSpriteFrameCount
        spriteFrameDuration: root.petSpriteFrameDuration
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 26

        MouseArea {
            id: petMouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
            property real pressScreenX: 0
            property real pressScreenY: 0
            property real pressWindowX: 0
            property real pressWindowY: 0

            onPressed: function(mouse) {
                pressScreenX = root.x + pet.x + mouse.x
                pressScreenY = root.y + pet.y + mouse.y
                pressWindowX = root.x
                pressWindowY = root.y
            }

            onPositionChanged: function(mouse) {
                if (!pressed) {
                    return
                }
                const currentScreenX = root.x + pet.x + mouse.x
                const currentScreenY = root.y + pet.y + mouse.y
                const dx = currentScreenX - pressScreenX
                const dy = currentScreenY - pressScreenY
                if (Math.abs(dx) > 4 || Math.abs(dy) > 4) {
                    compactBehavior.noteMovement()
                }
                root.x = root.clampWindowX(pressWindowX + dx, root.width)
                root.y = root.clampWindowY(pressWindowY + dy, root.height)
            }
        }
    }

    IconBubbleButton {
        id: settingsButton
        icon: "settings"
        tooltipText: settingsWindow.visible ? "Close settings" : "Open settings"
        enabled: root.controlsVisible
        opacity: root.controlsVisible ? 1 : 0
        anchors.right: pet.left
        anchors.rightMargin: -12
        anchors.top: pet.top
        anchors.topMargin: 18
        onClicked: root.toggleSettingsWindow()

        Behavior on opacity {
            NumberAnimation {
                duration: 140
                easing.type: Easing.OutQuad
            }
        }
    }

    IconBubbleButton {
        id: chatButton
        icon: "chat"
        tooltipText: chatWindow.visible ? "Close chat" : "Open chat"
        enabled: root.controlsVisible
        opacity: root.controlsVisible ? 1 : 0
        anchors.left: pet.right
        anchors.leftMargin: -12
        anchors.top: pet.top
        anchors.topMargin: 18
        onClicked: root.toggleChatWindow()

        Behavior on opacity {
            NumberAnimation {
                duration: 140
                easing.type: Easing.OutQuad
            }
        }
    }

    Rectangle {
        z: -1
        anchors.horizontalCenter: pet.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 20
        width: 116
        height: 14
        radius: 9
        color: "#000000"
        opacity: 0.14
    }
}
