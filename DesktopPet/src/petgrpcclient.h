#pragma once

#include <QByteArray>
#include <QObject>
#include <QString>

#include <atomic>
#include <memory>
#include <mutex>
#include <thread>

namespace grpc {
class Channel;
class ClientContext;
}

class PetGrpcClient : public QObject
{
    Q_OBJECT

public:
    explicit PetGrpcClient(QObject *parent = nullptr);
    ~PetGrpcClient() override;

    static QString normalizeTarget(QString target);

    QString target() const;
    void setTarget(const QString &target);

    bool streamConnected() const;

    void sendText(
        const QString &playerId,
        const QString &message);

    void sendVoice(
        const QString &playerId,
        const QByteArray &wavData,
        int durationMs,
        const QString &mode);

    void pullMessages(const QString &playerId, int maxMessages = 10);
    void connectMessageStream(const QString &playerId);
    void disconnectMessageStream();

signals:
    void textReplyReceived(
        const QString &reply,
        const QString &mood,
        const QByteArray &audio,
        const QString &audioMimeType);
    void voiceTranscriptReceived(const QString &transcript);
    void voiceReplyReceived(
        const QString &transcript,
        const QString &reply,
        const QString &mood,
        const QByteArray &audio,
        const QString &audioMimeType);
    void backendMessageReceived(
        const QString &text,
        const QString &mood,
        const QByteArray &audio,
        const QString &audioMimeType);
    void textRequestFailed(const QString &message, const QString &error);
    void voiceRequestFailed(const QString &error);
    void pullMessagesFinished(int count);
    void pullMessagesFailed(const QString &error);
    void streamConnectedChanged(bool connected);
    void streamFailed(const QString &error);

private:
    std::shared_ptr<grpc::Channel> channel() const;
    void setStreamConnected(bool connected);

    QString m_target = QStringLiteral("127.0.0.1:50051");
    mutable std::mutex m_channelMutex;
    std::shared_ptr<grpc::Channel> m_channel;

    std::atomic_bool m_streamStopRequested = false;
    std::atomic_bool m_streamConnected = false;
    std::thread m_streamThread;
    mutable std::mutex m_streamMutex;
    std::unique_ptr<grpc::ClientContext> m_streamContext;
};
