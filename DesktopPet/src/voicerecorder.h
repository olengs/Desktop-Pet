#pragma once

#include <QAudioFormat>
#include <QAudioSource>
#include <QByteArray>
#include <QElapsedTimer>
#include <QObject>
#include <QScopedPointer>
#include <QTimer>

class QIODevice;

class VoiceRecorder : public QObject
{
    Q_OBJECT
    Q_PROPERTY(bool listening READ listening NOTIFY listeningChanged)
    Q_PROPERTY(bool recording READ recording NOTIFY recordingChanged)
    Q_PROPERTY(bool voiceActivityEnabled READ voiceActivityEnabled NOTIFY voiceActivityEnabledChanged)
    Q_PROPERTY(qreal level READ level NOTIFY levelChanged)
    Q_PROPERTY(qreal vadThreshold READ vadThreshold WRITE setVadThreshold NOTIFY vadThresholdChanged)
    Q_PROPERTY(QString statusText READ statusText NOTIFY statusTextChanged)

public:
    explicit VoiceRecorder(QObject *parent = nullptr);

    bool listening() const;
    bool recording() const;
    bool voiceActivityEnabled() const;
    qreal level() const;
    qreal vadThreshold() const;
    void setVadThreshold(qreal threshold);
    QString statusText() const;

    Q_INVOKABLE void startPushToTalk();
    Q_INVOKABLE void stopPushToTalk();
    Q_INVOKABLE void startVoiceActivity();
    Q_INVOKABLE void stopVoiceActivity();

signals:
    void listeningChanged();
    void recordingChanged();
    void voiceActivityEnabledChanged();
    void levelChanged();
    void vadThresholdChanged();
    void statusTextChanged();
    void recordingFinished(const QByteArray &wavData, int durationMs, const QString &mode);
    void voiceError(const QString &message);

private:
    enum class CaptureMode {
        None,
        PushToTalk,
        VoiceActivity
    };

    void beginPushToTalkAfterPermission();
    void beginVoiceActivityAfterPermission();
    bool ensurePermission(void (VoiceRecorder::*continuation)());
    bool startCapture(CaptureMode mode);
    void stopCapture();
    void readAudio();
    void handleVadChunk(const QByteArray &chunk, qreal chunkLevel);
    void beginSegment(const QByteArray &firstChunk);
    void finishSegment(bool discard);
    QByteArray buildWavData(const QByteArray &pcmData) const;
    QString currentModeName() const;
    qreal calculateLevel(const QByteArray &chunk) const;
    void setListening(bool listening);
    void setRecording(bool recording);
    void setVoiceActivityEnabled(bool enabled);
    void setLevel(qreal level);
    void setStatusText(const QString &text);
    void fail(const QString &message);

    QScopedPointer<QAudioSource> m_audioSource;
    QIODevice *m_audioDevice = nullptr;
    QAudioFormat m_format;
    QElapsedTimer m_segmentTimer;
    QByteArray m_pcm;
    QByteArray m_preRoll;
    QTimer m_levelDecayTimer;
    CaptureMode m_mode = CaptureMode::None;
    bool m_listening = false;
    bool m_recording = false;
    bool m_voiceActivityEnabled = false;
    qreal m_level = 0.0;
    qreal m_vadThreshold = 0.08;
    QString m_statusText = QStringLiteral("Voice ready");
    int m_silenceMs = 0;
};
