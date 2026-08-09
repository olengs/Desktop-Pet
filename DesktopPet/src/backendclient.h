#pragma once

#include "petgrpcclient.h"

#include <QAudioOutput>
#include <QBuffer>
#include <QByteArray>
#include <QMediaPlayer>
#include <QObject>
#include <QString>

class BackendClient : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString backendTarget READ backendTarget WRITE setBackendTarget NOTIFY backendTargetChanged)
    Q_PROPERTY(QString playerId READ playerId WRITE setPlayerId NOTIFY playerIdChanged)
    Q_PROPERTY(bool online READ online NOTIFY onlineChanged)
    Q_PROPERTY(bool streamConnected READ streamConnected NOTIFY streamConnectedChanged)
    Q_PROPERTY(QString statusText READ statusText NOTIFY statusTextChanged)

public:
    explicit BackendClient(QObject *parent = nullptr);

    QString backendTarget() const;
    void setBackendTarget(const QString &backendTarget);

    QString playerId() const;
    void setPlayerId(const QString &playerId);

    bool online() const;
    bool streamConnected() const;
    QString statusText() const;

    Q_INVOKABLE void sendMessage(const QString &message);
    Q_INVOKABLE void pullMessages();
    Q_INVOKABLE void connectMessageStream();
    Q_INVOKABLE void disconnectMessageStream();

public slots:
    void uploadVoiceRecording(const QByteArray &wavData, int durationMs, const QString &mode);

signals:
    void backendTargetChanged();
    void playerIdChanged();
    void onlineChanged();
    void streamConnectedChanged();
    void statusTextChanged();

    void replyReceived(const QString &message, const QString &mood);
    void voiceTranscriptReceived(const QString &transcript);
    void chatError(const QString &message);

private:
    void setOnline(bool online);
    void setStreamConnected(bool connected);
    void setStatusText(const QString &statusText);

    QString fallbackReplyFor(const QString &message) const;

    void handleTextReply(
        const QString &reply,
        const QString &mood,
        const QByteArray &audio,
        const QString &audioMimeType);
    void handleVoiceReply(
        const QString &transcript,
        const QString &reply,
        const QString &mood,
        const QByteArray &audio,
        const QString &audioMimeType);
    void handleBackendMessage(
        const QString &text,
        const QString &mood,
        const QByteArray &audio,
        const QString &audioMimeType);
    void playAudioReply(const QByteArray &audio, const QString &audioMimeType);
    QUrl audioSourceHint(const QString &audioMimeType) const;

    PetGrpcClient m_grpc;
    QString m_backendTarget = QStringLiteral("127.0.0.1:50051");
    QString m_playerId = QStringLiteral("demo-player");
    QString m_statusText = QStringLiteral("Conversation ready");
    bool m_online = false;
    bool m_streamConnected = false;

    QByteArray m_replyAudioBytes;
    QBuffer m_replyAudioBuffer;
    QAudioOutput m_replyAudioOutput;
    QMediaPlayer m_replyPlayer;
};
