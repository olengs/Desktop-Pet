#include "backendclient.h"

#include <QIODevice>
#include <QUrl>

namespace {
QString moodOrDefault(const QString &mood)
{
    return mood.isEmpty() ? QStringLiteral("thinking") : mood;
}
}

BackendClient::BackendClient(QObject *parent)
    : QObject(parent)
    , m_grpc(this)
{
    m_grpc.setTarget(m_backendTarget);

    m_replyAudioOutput.setVolume(0.85);
    m_replyPlayer.setAudioOutput(&m_replyAudioOutput);
    connect(
        &m_replyPlayer,
        &QMediaPlayer::errorOccurred,
        this,
        [this](QMediaPlayer::Error, const QString &errorString) {
            if (errorString.isEmpty()) {
                return;
            }
            setStatusText(QStringLiteral("Audio reply could not play"));
            emit chatError(QStringLiteral("Audio reply could not play: %1").arg(errorString));
        });

    connect(&m_grpc, &PetGrpcClient::textReplyReceived, this, &BackendClient::handleTextReply);
    connect(&m_grpc, &PetGrpcClient::voiceTranscriptReceived, this, [this](const QString &transcript) {
        if (transcript.isEmpty()) {
            return;
        }
        setOnline(true);
        setStatusText(QStringLiteral("Voice transcript received"));
        emit voiceTranscriptReceived(transcript);
    });
    connect(&m_grpc, &PetGrpcClient::voiceReplyReceived, this, &BackendClient::handleVoiceReply);
    connect(&m_grpc, &PetGrpcClient::backendMessageReceived, this, &BackendClient::handleBackendMessage);

    connect(&m_grpc, &PetGrpcClient::textRequestFailed, this, [this](const QString &message, const QString &) {
        setOnline(false);
        setStatusText(QStringLiteral("gRPC backend unavailable; using local chat fallback"));
        emit replyReceived(fallbackReplyFor(message), QStringLiteral("thinking"));
    });

    connect(&m_grpc, &PetGrpcClient::voiceRequestFailed, this, [this](const QString &) {
        setOnline(false);
        setStatusText(QStringLiteral("Voice gRPC backend unavailable"));
        emit replyReceived(
            QStringLiteral("I received the voice note, but my speech-to-text backend is not awake yet. Type it for me while we wire up the Python side."),
            QStringLiteral("thinking"));
    });

    connect(&m_grpc, &PetGrpcClient::pullMessagesFinished, this, [this](int count) {
        setOnline(true);
        setStatusText(count == 0
            ? QStringLiteral("No pending gRPC messages")
            : QStringLiteral("Pulled %1 gRPC message%2").arg(count).arg(count == 1 ? QString() : QStringLiteral("s")));
    });

    connect(&m_grpc, &PetGrpcClient::pullMessagesFailed, this, [this](const QString &) {
        setOnline(false);
        setStatusText(QStringLiteral("Direct receive unavailable"));
    });

    connect(&m_grpc, &PetGrpcClient::streamConnectedChanged, this, [this](bool connected) {
        setStreamConnected(connected);
        setOnline(connected || m_online);
        setStatusText(connected
            ? QStringLiteral("gRPC receive stream connected")
            : QStringLiteral("gRPC receive stream disconnected"));
    });

    connect(&m_grpc, &PetGrpcClient::streamFailed, this, [this](const QString &) {
        setOnline(false);
        setStatusText(QStringLiteral("gRPC receive stream unavailable"));
    });
}

QString BackendClient::backendTarget() const
{
    return m_backendTarget;
}

void BackendClient::setBackendTarget(const QString &backendTarget)
{
    const QString normalized = PetGrpcClient::normalizeTarget(backendTarget);
    if (m_backendTarget == normalized) {
        return;
    }

    m_backendTarget = normalized;
    m_grpc.setTarget(m_backendTarget);
    emit backendTargetChanged();
    setStatusText(QStringLiteral("gRPC backend set to %1").arg(m_backendTarget));
}

QString BackendClient::playerId() const
{
    return m_playerId;
}

void BackendClient::setPlayerId(const QString &playerId)
{
    const QString normalized = playerId.trimmed().isEmpty() ? QStringLiteral("demo-player") : playerId.trimmed();
    if (m_playerId == normalized) {
        return;
    }

    m_playerId = normalized;
    emit playerIdChanged();
}

bool BackendClient::online() const
{
    return m_online;
}

bool BackendClient::streamConnected() const
{
    return m_streamConnected;
}

QString BackendClient::statusText() const
{
    return m_statusText;
}

void BackendClient::sendMessage(const QString &message)
{
    const QString trimmed = message.trimmed();
    if (trimmed.isEmpty()) {
        return;
    }

    setStatusText(QStringLiteral("Sending text over gRPC..."));
    m_grpc.sendText(m_playerId, trimmed);
}

void BackendClient::uploadVoiceRecording(const QByteArray &wavData, int durationMs, const QString &mode)
{
    if (wavData.isEmpty()) {
        emit chatError(QStringLiteral("Voice recording was empty"));
        return;
    }

    setStatusText(QStringLiteral("Sending WAV over gRPC..."));
    m_grpc.sendVoice(m_playerId, wavData, durationMs, mode);
}

void BackendClient::pullMessages()
{
    setStatusText(QStringLiteral("Pulling gRPC messages..."));
    m_grpc.pullMessages(m_playerId);
}

void BackendClient::connectMessageStream()
{
    setStatusText(QStringLiteral("Connecting gRPC receive stream..."));
    m_grpc.connectMessageStream(m_playerId);
}

void BackendClient::disconnectMessageStream()
{
    m_grpc.disconnectMessageStream();
}

void BackendClient::setOnline(bool online)
{
    if (m_online == online) {
        return;
    }

    m_online = online;
    emit onlineChanged();
}

void BackendClient::setStreamConnected(bool connected)
{
    if (m_streamConnected == connected) {
        return;
    }

    m_streamConnected = connected;
    emit streamConnectedChanged();
}

void BackendClient::setStatusText(const QString &statusText)
{
    if (m_statusText == statusText) {
        return;
    }

    m_statusText = statusText;
    emit statusTextChanged();
}

QString BackendClient::fallbackReplyFor(const QString &message) const
{
    const QString lower = message.toLower();
    if (lower.contains(QStringLiteral("hello"))
        || lower == QStringLiteral("hi")
        || lower.startsWith(QStringLiteral("hi "))
        || lower.contains(QStringLiteral(" hey"))
        || lower.startsWith(QStringLiteral("hey"))) {
        return QStringLiteral("Hey, I am Mimo. My AI backend is offline, but I can still keep you company for a moment.");
    }

    if (lower.contains(QStringLiteral("remember")) || lower.contains(QStringLiteral("memory"))) {
        return QStringLiteral("I do not keep local memories on the desktop pet. When the backend is connected, it handles our chat context.");
    }

    if (lower.contains(QStringLiteral("help")) || lower.contains(QStringLiteral("stuck")) || lower.contains(QStringLiteral("focus"))) {
        return QStringLiteral("I am in local fallback mode right now, but we can still untangle this. Tell me the smallest next thing you want to figure out.");
    }

    if (lower.contains(QStringLiteral("tired")) || lower.contains(QStringLiteral("stress")) || lower.contains(QStringLiteral("overwhelmed"))) {
        return QStringLiteral("That sounds like a lot. Take one slow breath with me, then tell me what part is weighing on you most.");
    }

    return QStringLiteral("My AI backend is not connected right now, but I am here. Tell me what is on your mind, or try again once the backend is running.");
}

void BackendClient::handleTextReply(
    const QString &reply,
    const QString &mood,
    const QByteArray &audio,
    const QString &audioMimeType)
{
    setOnline(true);
    setStatusText(QStringLiteral("gRPC text reply received"));

    if (!reply.isEmpty()) {
        emit replyReceived(reply, moodOrDefault(mood));
    } else if (!audio.isEmpty()) {
        emit replyReceived(QStringLiteral("Mimo sent an audio reply."), moodOrDefault(mood));
    } else {
        emit replyReceived(QStringLiteral("I received your message."), moodOrDefault(mood));
    }

    playAudioReply(audio, audioMimeType);
}

void BackendClient::handleVoiceReply(
    const QString &transcript,
    const QString &reply,
    const QString &mood,
    const QByteArray &audio,
    const QString &audioMimeType)
{
    setOnline(true);
    setStatusText(QStringLiteral("gRPC voice reply received"));

    if (!transcript.isEmpty()) {
        emit voiceTranscriptReceived(transcript);
    }

    if (!reply.isEmpty()) {
        emit replyReceived(reply, moodOrDefault(mood));
    } else if (!audio.isEmpty()) {
        emit replyReceived(QStringLiteral("Mimo sent an audio reply."), moodOrDefault(mood));
    } else {
        emit replyReceived(
            transcript.isEmpty() ? QStringLiteral("I received your voice note.") : fallbackReplyFor(transcript),
            moodOrDefault(mood));
    }

    playAudioReply(audio, audioMimeType);
}

void BackendClient::handleBackendMessage(
    const QString &text,
    const QString &mood,
    const QByteArray &audio,
    const QString &audioMimeType)
{
    setOnline(true);
    setStatusText(QStringLiteral("gRPC backend message received"));

    if (!text.isEmpty()) {
        emit replyReceived(text, moodOrDefault(mood));
    } else if (!audio.isEmpty()) {
        emit replyReceived(QStringLiteral("Mimo sent an audio message."), moodOrDefault(mood));
    }

    playAudioReply(audio, audioMimeType);
}

void BackendClient::playAudioReply(const QByteArray &audio, const QString &audioMimeType)
{
    if (audio.isEmpty()) {
        return;
    }

    m_replyPlayer.stop();
    m_replyPlayer.setSource(QUrl());
    m_replyAudioBuffer.close();
    m_replyAudioBytes = audio;
    m_replyAudioBuffer.setData(m_replyAudioBytes);
    if (!m_replyAudioBuffer.open(QIODevice::ReadOnly)) {
        emit chatError(QStringLiteral("Could not prepare Mimo audio reply"));
        return;
    }
    m_replyAudioBuffer.seek(0);

    m_replyPlayer.setSourceDevice(&m_replyAudioBuffer, audioSourceHint(audioMimeType, ++m_replyAudioSerial));
    m_replyPlayer.setPosition(0);
    m_replyPlayer.play();
}

QUrl BackendClient::audioSourceHint(const QString &audioMimeType, quint64 serial) const
{
    const QString lower = audioMimeType.toLower();
    if (lower.contains(QStringLiteral("mpeg")) || lower.contains(QStringLiteral("mp3"))) {
        return QUrl(QStringLiteral("mimo-reply-%1.mp3").arg(serial));
    }
    if (lower.contains(QStringLiteral("ogg"))) {
        return QUrl(QStringLiteral("mimo-reply-%1.ogg").arg(serial));
    }
    return QUrl(QStringLiteral("mimo-reply-%1.wav").arg(serial));
}
