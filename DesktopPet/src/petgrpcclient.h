#pragma once

#include <QByteArray>
#include <QObject>
#include <QString>
#include <QStringList>

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
    struct TraitSnapshot {
        int teamwork = 0;
        int aggression = 0;
        int loyalty = 0;
        int leadership = 0;
        int riskTaking = 0;
    };

    explicit PetGrpcClient(QObject *parent = nullptr);
    ~PetGrpcClient() override;

    static QString normalizeTarget(QString target);

    QString target() const;
    void setTarget(const QString &target);

    bool streamConnected() const;

    void sendText(
        const QString &playerId,
        const QString &message,
        const QStringList &memoryContext,
        const TraitSnapshot &traits);

    void sendVoice(
        const QString &playerId,
        const QByteArray &wavData,
        int durationMs,
        const QString &mode,
        const QStringList &memoryContext,
        const TraitSnapshot &traits);

    void sendGameEvent(
        const QString &playerId,
        const QString &game,
        const QString &eventType,
        const QString &summary,
        const TraitSnapshot &impact);

    void pullMessages(const QString &playerId, int maxMessages = 10);
    void connectMessageStream(const QString &playerId);
    void disconnectMessageStream();

signals:
    void textReplyReceived(
        const QString &reply,
        const QString &mood,
        const QByteArray &audio,
        const QString &audioMimeType);
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
    void gameEventAccepted(const QString &summary, const QString &mood);
    void textRequestFailed(const QString &message, const QString &error);
    void voiceRequestFailed(const QString &error);
    void gameEventRequestFailed(const QString &summary, const QString &error);
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
