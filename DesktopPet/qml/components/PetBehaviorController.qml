pragma ComponentBehavior: Bound

import QtQuick

Item {
    id: root

    property bool compactMode: false

    property string normalPose: "sit"
    property string normalMood: "idle"
    property string sleepPose: "sleep"
    property string sleepMood: "idle"
    property string disturbedPose: "annoyed"
    property string disturbedMood: "annoyed"
    property int sleepDelayMs: 12000
    property int disturbedDurationMs: 2400

    readonly property string pose: currentState === "sleeping"
        ? sleepPose
        : currentState === "disturbed" ? disturbedPose : normalPose
    readonly property string mood: currentState === "sleeping"
        ? sleepMood
        : currentState === "disturbed" ? disturbedMood : normalMood
    readonly property bool sleeping: compactMode && currentState === "sleeping"
    readonly property bool disturbed: compactMode && currentState === "disturbed"

    width: 0
    height: 0
    visible: false

    property string currentState: "normal"

    onCompactModeChanged: {
        if (compactMode) {
            resetToNormal()
        } else {
            stopTimers()
            currentState = "normal"
        }
    }

    function noteMovement() {
        if (!compactMode) {
            return
        }

        if (sleeping) {
            becomeDisturbed()
            return
        }

        if (disturbed) {
            restartDisturbedTimer()
            return
        }

        restartSleepTimer()
    }

    function resetToNormal() {
        currentState = "normal"
        if (compactMode) {
            restartSleepTimer()
        }
    }

    function becomeDisturbed() {
        currentState = "disturbed"
        sleepTimer.stop()
        restartDisturbedTimer()
    }

    function restartSleepTimer() {
        sleepTimer.interval = Math.max(1, sleepDelayMs)
        sleepTimer.restart()
    }

    function restartDisturbedTimer() {
        disturbedTimer.interval = Math.max(1, disturbedDurationMs)
        disturbedTimer.restart()
    }

    function stopTimers() {
        sleepTimer.stop()
        disturbedTimer.stop()
    }

    Timer {
        id: sleepTimer
        interval: root.sleepDelayMs
        repeat: false
        onTriggered: {
            if (root.compactMode && !root.disturbed) {
                root.currentState = "sleeping"
            }
        }
    }

    Timer {
        id: disturbedTimer
        interval: root.disturbedDurationMs
        repeat: false
        onTriggered: root.resetToNormal()
    }
}
