#include "voicerecorder.h"

#include <QAudioDevice>
#if QT_VERSION < QT_VERSION_CHECK(6, 7, 0)
#include <QAudio>
#endif
#include <QBuffer>
#include <QCoreApplication>
#include <QDataStream>
#include <QIODevice>
#include <QMediaDevices>
#include <QPermissions>

#include <algorithm>
#include <cmath>
#include <vector>

namespace {
constexpr int FallbackSampleRate = 48000;
constexpr int CanonicalVoiceSampleRate = 16000;
constexpr int CanonicalVoiceChannels = 1;
constexpr int CanonicalVoiceBitsPerSample = 16;
constexpr int LevelDecayMs = 80;
constexpr int VadChunkMs = 50;
constexpr int VadSilenceToStopMs = 850;
constexpr int MinimumSegmentMs = 450;
constexpr int MaximumPreRollMs = 280;

#if QT_VERSION < QT_VERSION_CHECK(6, 7, 0)
using AudioState = QAudio::State;
constexpr auto StoppedState = QAudio::StoppedState;
constexpr auto NoError = QAudio::NoError;
#else
using AudioState = QtAudio::State;
constexpr auto StoppedState = QtAudio::StoppedState;
constexpr auto NoError = QtAudio::NoError;
#endif
}

VoiceRecorder::VoiceRecorder(QObject *parent)
    : QObject(parent)
{
    m_levelDecayTimer.setInterval(LevelDecayMs);
    connect(&m_levelDecayTimer, &QTimer::timeout, this, [this]() {
        if (!m_listening) {
            setLevel(0.0);
            m_levelDecayTimer.stop();
            return;
        }
        setLevel(std::max<qreal>(0.0, m_level * 0.78));
    });
}

bool VoiceRecorder::listening() const
{
    return m_listening;
}

bool VoiceRecorder::recording() const
{
    return m_recording;
}

bool VoiceRecorder::voiceActivityEnabled() const
{
    return m_voiceActivityEnabled;
}

qreal VoiceRecorder::level() const
{
    return m_level;
}

qreal VoiceRecorder::vadThreshold() const
{
    return m_vadThreshold;
}

void VoiceRecorder::setVadThreshold(qreal threshold)
{
    const qreal normalized = std::clamp(threshold, 0.02, 0.4);
    if (qFuzzyCompare(m_vadThreshold, normalized)) {
        return;
    }
    m_vadThreshold = normalized;
    emit vadThresholdChanged();
}

QString VoiceRecorder::statusText() const
{
    return m_statusText;
}

void VoiceRecorder::startPushToTalk()
{
    if (!ensurePermission(&VoiceRecorder::beginPushToTalkAfterPermission)) {
        return;
    }
    beginPushToTalkAfterPermission();
}

void VoiceRecorder::stopPushToTalk()
{
    if (m_mode != CaptureMode::PushToTalk) {
        return;
    }
    finishSegment(m_segmentTimer.elapsed() < MinimumSegmentMs);
    stopCapture();
}

void VoiceRecorder::startVoiceActivity()
{
    if (!ensurePermission(&VoiceRecorder::beginVoiceActivityAfterPermission)) {
        return;
    }
    beginVoiceActivityAfterPermission();
}

void VoiceRecorder::stopVoiceActivity()
{
    if (m_mode == CaptureMode::VoiceActivity && m_recording) {
        finishSegment(m_segmentTimer.elapsed() < MinimumSegmentMs);
    }
    stopCapture();
    setVoiceActivityEnabled(false);
    setStatusText(QStringLiteral("Voice ready"));
}

void VoiceRecorder::beginPushToTalkAfterPermission()
{
    if (m_mode == CaptureMode::VoiceActivity) {
        stopVoiceActivity();
    }
    if (!startCapture(CaptureMode::PushToTalk)) {
        return;
    }
    m_pcm.clear();
    m_segmentTimer.restart();
    setRecording(true);
    setStatusText(QStringLiteral("Listening while held"));
}

void VoiceRecorder::beginVoiceActivityAfterPermission()
{
    if (m_mode == CaptureMode::PushToTalk) {
        stopPushToTalk();
    }
    if (m_mode == CaptureMode::VoiceActivity) {
        setVoiceActivityEnabled(true);
        return;
    }
    if (!startCapture(CaptureMode::VoiceActivity)) {
        setVoiceActivityEnabled(false);
        return;
    }
    setVoiceActivityEnabled(true);
    setStatusText(QStringLiteral("Listen mode on"));
}

bool VoiceRecorder::ensurePermission(void (VoiceRecorder::*continuation)())
{
    QMicrophonePermission microphonePermission;
    switch (qApp->checkPermission(microphonePermission)) {
    case Qt::PermissionStatus::Granted:
        return true;
    case Qt::PermissionStatus::Denied:
        fail(QStringLiteral("Microphone permission denied"));
        return false;
    case Qt::PermissionStatus::Undetermined:
        setStatusText(QStringLiteral("Requesting microphone permission"));
        qApp->requestPermission(microphonePermission, this, continuation);
        return false;
    }
    return false;
}

bool VoiceRecorder::startCapture(CaptureMode mode)
{
    if (m_listening && m_mode == mode) {
        return true;
    }
    stopCapture();

    const QAudioDevice inputDevice = QMediaDevices::defaultAudioInput();
    if (inputDevice.isNull()) {
        fail(QStringLiteral("No microphone found"));
        return false;
    }

    m_format = inputDevice.preferredFormat();
    if (!m_format.isValid()) {
        m_format.setSampleRate(FallbackSampleRate);
        m_format.setChannelCount(1);
        m_format.setSampleFormat(QAudioFormat::Int16);
    }

    if (!m_format.isValid()) {
        fail(QStringLiteral("Microphone format is unavailable"));
        return false;
    }

    m_audioSource.reset(new QAudioSource(inputDevice, m_format, this));
    connect(m_audioSource.data(), &QAudioSource::stateChanged, this, [this](AudioState state) {
        if (state == StoppedState && m_audioSource && m_audioSource->error() != NoError) {
            fail(QStringLiteral("Microphone capture stopped unexpectedly"));
        }
    });

    m_audioDevice = m_audioSource->start();
    if (!m_audioDevice) {
        fail(QStringLiteral("Could not start microphone capture"));
        return false;
    }

    connect(m_audioDevice, &QIODevice::readyRead, this, &VoiceRecorder::readAudio);
    m_mode = mode;
    m_silenceMs = 0;
    m_preRoll.clear();
    setListening(true);
    m_levelDecayTimer.start();
    return true;
}

void VoiceRecorder::stopCapture()
{
    if (m_audioSource) {
        m_audioSource->stop();
    }
    m_audioDevice = nullptr;
    m_audioSource.reset();
    m_pcm.clear();
    m_preRoll.clear();
    m_silenceMs = 0;
    m_mode = CaptureMode::None;
    setRecording(false);
    setListening(false);
}

void VoiceRecorder::readAudio()
{
    if (!m_audioDevice) {
        return;
    }

    const QByteArray chunk = m_audioDevice->readAll();
    if (chunk.isEmpty()) {
        return;
    }

    const qreal chunkLevel = calculateLevel(chunk);
    setLevel(std::max(m_level, chunkLevel));

    if (m_mode == CaptureMode::PushToTalk && m_recording) {
        m_pcm.append(chunk);
        return;
    }

    if (m_mode == CaptureMode::VoiceActivity) {
        handleVadChunk(chunk, chunkLevel);
    }
}

void VoiceRecorder::handleVadChunk(const QByteArray &chunk, qreal chunkLevel)
{
    const int bytesPerMs = std::max(1, (m_format.sampleRate() * m_format.bytesPerFrame()) / 1000);
    const int maxPreRollBytes = bytesPerMs * MaximumPreRollMs;
    m_preRoll.append(chunk);
    if (m_preRoll.size() > maxPreRollBytes) {
        m_preRoll.remove(0, m_preRoll.size() - maxPreRollBytes);
    }

    const bool voiceDetected = chunkLevel >= m_vadThreshold;
    if (!m_recording && voiceDetected) {
        beginSegment(m_preRoll);
        m_preRoll.clear();
        setStatusText(QStringLiteral("I hear you"));
        return;
    }

    if (!m_recording) {
        return;
    }

    m_pcm.append(chunk);
    if (voiceDetected) {
        m_silenceMs = 0;
        return;
    }

    m_silenceMs += VadChunkMs;
    if (m_silenceMs >= VadSilenceToStopMs) {
        finishSegment(m_segmentTimer.elapsed() < MinimumSegmentMs);
        setStatusText(QStringLiteral("Listen mode on"));
    }
}

void VoiceRecorder::beginSegment(const QByteArray &firstChunk)
{
    m_pcm.clear();
    m_pcm.append(firstChunk);
    m_silenceMs = 0;
    m_segmentTimer.restart();
    setRecording(true);
}

void VoiceRecorder::finishSegment(bool discard)
{
    if (!m_recording) {
        return;
    }

    const int durationMs = static_cast<int>(m_segmentTimer.elapsed());
    setRecording(false);

    if (discard || m_pcm.isEmpty()) {
        m_pcm.clear();
        setStatusText(m_mode == CaptureMode::VoiceActivity
            ? QStringLiteral("Listen mode on")
            : QStringLiteral("Voice ready"));
        return;
    }

    const QByteArray wavData = buildWavData(m_pcm);
    m_pcm.clear();
    if (wavData.isEmpty()) {
        fail(QStringLiteral("Could not prepare voice note"));
        return;
    }

    emit recordingFinished(wavData, durationMs, currentModeName());
    setStatusText(QStringLiteral("Voice note sent"));
}

QByteArray VoiceRecorder::convertToCanonicalPcm16Mono(const QByteArray &pcmData) const
{
    if (!m_format.isValid() || m_format.bytesPerFrame() <= 0 || m_format.sampleRate() <= 0 || pcmData.isEmpty()) {
        return {};
    }

    const int sourceChannels = std::max(1, m_format.channelCount());
    const int sourceBytesPerSample = std::max(1, m_format.bytesPerSample());
    const int sourceBytesPerFrame = m_format.bytesPerFrame();
    const int sourceFrameCount = pcmData.size() / sourceBytesPerFrame;
    if (sourceFrameCount <= 0) {
        return {};
    }

    std::vector<float> monoSamples;
    monoSamples.reserve(static_cast<std::size_t>(sourceFrameCount));
    const char *raw = pcmData.constData();
    for (int frame = 0; frame < sourceFrameCount; ++frame) {
        const char *frameStart = raw + frame * sourceBytesPerFrame;
        double sum = 0.0;
        for (int channel = 0; channel < sourceChannels; ++channel) {
            const char *sample = frameStart + channel * sourceBytesPerSample;
            sum += static_cast<double>(m_format.normalizedSampleValue(sample));
        }
        monoSamples.push_back(static_cast<float>(std::clamp(sum / sourceChannels, -1.0, 1.0)));
    }

    const int targetFrameCount = std::max(
        1,
        static_cast<int>(std::llround(
            static_cast<double>(monoSamples.size()) * CanonicalVoiceSampleRate / m_format.sampleRate())));

    QByteArray canonicalPcm;
    canonicalPcm.reserve(targetFrameCount * 2);
    QDataStream out(&canonicalPcm, QIODevice::WriteOnly);
    out.setByteOrder(QDataStream::LittleEndian);

    for (int frame = 0; frame < targetFrameCount; ++frame) {
        const double sourcePosition = static_cast<double>(frame) * m_format.sampleRate() / CanonicalVoiceSampleRate;
        const int leftIndex = std::clamp(
            static_cast<int>(std::floor(sourcePosition)),
            0,
            static_cast<int>(monoSamples.size()) - 1);
        const int rightIndex = std::min(leftIndex + 1, static_cast<int>(monoSamples.size()) - 1);
        const double fraction = sourcePosition - leftIndex;
        const double value = monoSamples[leftIndex] + (monoSamples[rightIndex] - monoSamples[leftIndex]) * fraction;
        const qint16 sample = static_cast<qint16>(std::llround(std::clamp(value, -1.0, 1.0) * 32767.0));
        out << sample;
    }

    return canonicalPcm;
}

QByteArray VoiceRecorder::buildWavData(const QByteArray &pcmData) const
{
    const QByteArray canonicalPcm = convertToCanonicalPcm16Mono(pcmData);
    if (canonicalPcm.isEmpty()) {
        return {};
    }

    QByteArray wavData;
    QBuffer buffer(&wavData);
    if (!buffer.open(QIODevice::WriteOnly)) {
        return {};
    }

    const quint16 audioFormat = 1;
    const quint16 channelCount = CanonicalVoiceChannels;
    const quint32 sampleRate = CanonicalVoiceSampleRate;
    const quint16 blockAlign = channelCount * (CanonicalVoiceBitsPerSample / 8);
    const quint16 bitsPerSample = CanonicalVoiceBitsPerSample;
    const quint32 byteRate = sampleRate * blockAlign;
    const quint32 dataSize = static_cast<quint32>(canonicalPcm.size());

    QDataStream out(&buffer);
    out.setByteOrder(QDataStream::LittleEndian);

    buffer.write("RIFF", 4);
    out << quint32(36 + dataSize);
    buffer.write("WAVE", 4);
    buffer.write("fmt ", 4);
    out << quint32(16);
    out << audioFormat;
    out << channelCount;
    out << sampleRate;
    out << byteRate;
    out << blockAlign;
    out << bitsPerSample;
    buffer.write("data", 4);
    out << dataSize;
    buffer.write(canonicalPcm);

    return wavData;
}

QString VoiceRecorder::currentModeName() const
{
    switch (m_mode) {
    case CaptureMode::PushToTalk:
        return QStringLiteral("push_to_talk");
    case CaptureMode::VoiceActivity:
        return QStringLiteral("voice_activity");
    case CaptureMode::None:
        break;
    }
    return QStringLiteral("none");
}

qreal VoiceRecorder::calculateLevel(const QByteArray &chunk) const
{
    if (!m_format.isValid() || m_format.bytesPerFrame() <= 0 || chunk.isEmpty()) {
        return 0.0;
    }

    const int frameCount = chunk.size() / m_format.bytesPerFrame();
    if (frameCount <= 0) {
        return 0.0;
    }

    double sum = 0.0;
    const char *samples = chunk.constData();
    for (int frame = 0; frame < frameCount; ++frame) {
        const float value = m_format.normalizedSampleValue(samples + frame * m_format.bytesPerFrame());
        sum += static_cast<double>(value) * static_cast<double>(value);
    }

    return std::clamp<qreal>(std::sqrt(sum / frameCount), 0.0, 1.0);
}

void VoiceRecorder::setListening(bool listening)
{
    if (m_listening == listening) {
        return;
    }
    m_listening = listening;
    emit listeningChanged();
}

void VoiceRecorder::setRecording(bool recording)
{
    if (m_recording == recording) {
        return;
    }
    m_recording = recording;
    emit recordingChanged();
}

void VoiceRecorder::setVoiceActivityEnabled(bool enabled)
{
    if (m_voiceActivityEnabled == enabled) {
        return;
    }
    m_voiceActivityEnabled = enabled;
    emit voiceActivityEnabledChanged();
}

void VoiceRecorder::setLevel(qreal level)
{
    const qreal normalized = std::clamp(level, 0.0, 1.0);
    if (std::abs(m_level - normalized) < 0.01) {
        return;
    }
    m_level = normalized;
    emit levelChanged();
}

void VoiceRecorder::setStatusText(const QString &text)
{
    if (m_statusText == text) {
        return;
    }
    m_statusText = text;
    emit statusTextChanged();
}

void VoiceRecorder::fail(const QString &message)
{
    stopCapture();
    setVoiceActivityEnabled(false);
    setStatusText(message);
    emit voiceError(message);
}
