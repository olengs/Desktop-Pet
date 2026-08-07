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
    connect(&m_grpc, &PetGrpcClient::voiceReplyReceived, this, &BackendClient::handleVoiceReply);
    connect(&m_grpc, &PetGrpcClient::backendMessageReceived, this, &BackendClient::handleBackendMessage);

    connect(&m_grpc, &PetGrpcClient::gameEventAccepted, this, [this](const QString &summary, const QString &mood) {
        setOnline(true);
        setStatusText(QStringLiteral("Event saved to gRPC backend"));
        emit eventAccepted(summary, moodOrDefault(mood));
    });

    connect(&m_grpc, &PetGrpcClient::textRequestFailed, this, [this](const QString &message, const QString &) {
        setOnline(false);
        setStatusText(QStringLiteral("gRPC backend unavailable; using local demo memory"));
        emit replyReceived(fallbackReplyFor(message), QStringLiteral("thinking"));
    });

    connect(&m_grpc, &PetGrpcClient::voiceRequestFailed, this, [this](const QString &) {
        setOnline(false);
        setStatusText(QStringLiteral("Voice gRPC backend unavailable"));
        emit replyReceived(
            QStringLiteral("I received the voice note, but my speech-to-text backend is not awake yet. Type it for me while we wire up the Python side."),
            QStringLiteral("thinking"));
    });

    connect(&m_grpc, &PetGrpcClient::gameEventRequestFailed, this, [this](const QString &, const QString &) {
        setOnline(false);
        setStatusText(QStringLiteral("gRPC backend unavailable; event kept in local demo memory"));
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
    m_grpc.sendText(m_playerId, trimmed, memoryContext(), traitSnapshot());
}

void BackendClient::uploadVoiceRecording(const QByteArray &wavData, int durationMs, const QString &mode)
{
    if (wavData.isEmpty()) {
        emit chatError(QStringLiteral("Voice recording was empty"));
        return;
    }

    setStatusText(QStringLiteral("Sending WAV over gRPC..."));
    m_grpc.sendVoice(m_playerId, wavData, durationMs, mode, memoryContext(), traitSnapshot());
}

void BackendClient::sendDemoEvent(const QString &eventType)
{
    const DemoEvent event = demoEventFor(eventType);
    rememberDemoEvent(event);
    emit eventAccepted(event.summary, event.mood);
    setStatusText(QStringLiteral("Sending %1 event over gRPC...").arg(event.game));

    m_grpc.sendGameEvent(m_playerId, event.game, event.type, event.summary, impactSnapshot(event));
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

BackendClient::DemoEvent BackendClient::demoEventFor(const QString &eventType) const
{
    if (eventType == QStringLiteral("ignored_teammate_revive")) {
        return {
            QStringLiteral("ignored_teammate_revive"),
            QStringLiteral("Free Fire"),
            QStringLiteral("You skipped a teammate revive to chase a fight."),
            QStringLiteral("annoyed"),
            -2,
            1,
            -1,
            0,
            1,
        };
    }

    if (eventType == QStringLiteral("revived_teammate")) {
        return {
            QStringLiteral("revived_teammate"),
            QStringLiteral("Free Fire"),
            QStringLiteral("You crossed open ground to revive a teammate."),
            QStringLiteral("happy"),
            2,
            0,
            2,
            1,
            1,
        };
    }

    if (eventType == QStringLiteral("shotcaller_win")) {
        return {
            QStringLiteral("shotcaller_win"),
            QStringLiteral("Arena of Valor"),
            QStringLiteral("You called the final push and the team closed the match."),
            QStringLiteral("happy"),
            1,
            1,
            1,
            3,
            0,
        };
    }

    return {
        QStringLiteral("rushed_alone"),
        QStringLiteral("Free Fire"),
        QStringLiteral("You rushed alone before your squad was ready."),
        QStringLiteral("thinking"),
        -1,
        2,
        0,
        0,
        2,
    };
}

void BackendClient::rememberDemoEvent(const DemoEvent &event)
{
    m_teamwork += event.teamwork;
    m_aggression += event.aggression;
    m_loyalty += event.loyalty;
    m_leadership += event.leadership;
    m_riskTaking += event.riskTaking;

    m_memories.prepend(event.summary);
    while (m_memories.size() > 6) {
        m_memories.removeLast();
    }
}

QString BackendClient::fallbackReplyFor(const QString &message) const
{
    const QString lower = message.toLower();
    if (lower.contains(QStringLiteral("how")) && (lower.contains(QStringLiteral("playing")) || lower.contains(QStringLiteral("play")))) {
        return QStringLiteral("You are playing with sharp instincts. %1 I would pair you with a calm teammate who can keep the squad shape around your pushes.").arg(strongestTraitLine());
    }

    if (lower.contains(QStringLiteral("team")) || lower.contains(QStringLiteral("friend")) || lower.contains(QStringLiteral("match"))) {
        return QStringLiteral("For teammates, I would look for someone with steady teamwork and similar play time. Your current profile says: %1").arg(strongestTraitLine());
    }

    if (lower.contains(QStringLiteral("remember")) || lower.contains(QStringLiteral("memory"))) {
        if (m_memories.isEmpty()) {
            return QStringLiteral("I do not have match memories yet. Send me a fake event and I will start building your player profile.");
        }
        return QStringLiteral("Latest memory: %1").arg(m_memories.first());
    }

    if (lower.contains(QStringLiteral("hello")) || lower.contains(QStringLiteral("hi"))) {
        return QStringLiteral("Hey, I am awake and parked on your desktop. Send me a demo match event and I will start judging your playstyle gently.");
    }

    if (m_memories.isEmpty()) {
        return QStringLiteral("I am in local demo mode right now. Give me a fake game event and I can react with memory-backed banter.");
    }

    return QStringLiteral("%1 Also, I remember this: %2").arg(strongestTraitLine(), m_memories.first());
}

QString BackendClient::strongestTraitLine() const
{
    const int aggressiveSignal = m_aggression + m_riskTaking;
    const int supportSignal = m_teamwork + m_loyalty + m_leadership;

    if (aggressiveSignal >= supportSignal + 2) {
        return QStringLiteral("Your aggression and risk-taking are trending high.");
    }

    if (supportSignal >= aggressiveSignal + 2) {
        return QStringLiteral("Your teamwork and loyalty are becoming your strongest traits.");
    }

    if (m_leadership >= 3) {
        return QStringLiteral("Your leadership score is starting to stand out.");
    }

    return QStringLiteral("Your profile is still balanced, with a slight lean toward bold plays.");
}

QStringList BackendClient::memoryContext() const
{
    return m_memories;
}

PetGrpcClient::TraitSnapshot BackendClient::traitSnapshot() const
{
    return {
        m_teamwork,
        m_aggression,
        m_loyalty,
        m_leadership,
        m_riskTaking,
    };
}

PetGrpcClient::TraitSnapshot BackendClient::impactSnapshot(const DemoEvent &event) const
{
    return {
        event.teamwork,
        event.aggression,
        event.loyalty,
        event.leadership,
        event.riskTaking,
    };
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
    m_replyAudioBuffer.close();
    m_replyAudioBytes = audio;
    m_replyAudioBuffer.setData(m_replyAudioBytes);
    if (!m_replyAudioBuffer.open(QIODevice::ReadOnly)) {
        emit chatError(QStringLiteral("Could not prepare Mimo audio reply"));
        return;
    }

    m_replyPlayer.setSourceDevice(&m_replyAudioBuffer, audioSourceHint(audioMimeType));
    m_replyPlayer.play();
}

QUrl BackendClient::audioSourceHint(const QString &audioMimeType) const
{
    const QString lower = audioMimeType.toLower();
    if (lower.contains(QStringLiteral("mpeg")) || lower.contains(QStringLiteral("mp3"))) {
        return QUrl(QStringLiteral("mimo-reply.mp3"));
    }
    if (lower.contains(QStringLiteral("ogg"))) {
        return QUrl(QStringLiteral("mimo-reply.ogg"));
    }
    return QUrl(QStringLiteral("mimo-reply.wav"));
}
