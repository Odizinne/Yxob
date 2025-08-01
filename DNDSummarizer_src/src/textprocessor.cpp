#include "textprocessor.h"
#include <QFile>
#include <QTextStream>
#include <QRegularExpression>
#include <QDebug>
#include <QFileInfo>

TextProcessor::TextProcessor(QObject *parent)
    : QObject(parent)
{
}

QString TextProcessor::combineTranscripts(const QStringList &filePaths)
{
    QList<TranscriptEntry> allEntries;
    QStringList participants;

    for (const QString &filePath : filePaths) {
        QList<TranscriptEntry> entries = parseTranscriptFile(filePath);

        QFileInfo fileInfo(filePath);
        QString fileName = fileInfo.baseName();
        QStringList parts = fileName.split('_');
        QString participant = parts.isEmpty() ? fileName : parts.last();

        if (!participants.contains(participant)) {
            participants.append(participant);
        }

        for (auto &entry : entries) {
            entry.participant = participant;
            allEntries.append(entry);
        }
    }

    std::sort(allEntries.begin(), allEntries.end(),
              [](const TranscriptEntry &a, const TranscriptEntry &b) {
                  return a.startSeconds < b.startSeconds;
              });

    QString combined = QString("Session D&D avec %1\n").arg(participants.join(", "));
    combined += QString("=").repeated(50) + "\n\n";

    for (const auto &entry : allEntries) {
        combined += QString("[%1 -> %2] %3: %4\n\n")
        .arg(entry.startTime, entry.endTime, entry.participant, entry.text);
    }

    return combined;
}

QList<TranscriptEntry> TextProcessor::parseTranscriptFile(const QString &filePath)
{
    QList<TranscriptEntry> entries;

    QFile file(filePath);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        qWarning() << "Cannot open file:" << filePath;
        return entries;
    }

    QTextStream stream(&file);
    stream.setEncoding(QStringConverter::Utf8);
    QString content = stream.readAll();

    QRegularExpression timestampRegex(R"(\[(\d{2}:\d{2}(?::\d{2})?)\s*->\s*(\d{2}:\d{2}(?::\d{2})?)\]\s*(.+?)(?=\n\[|\Z))",
                                      QRegularExpression::DotMatchesEverythingOption);

    QRegularExpressionMatchIterator iterator = timestampRegex.globalMatch(content);

    while (iterator.hasNext()) {
        QRegularExpressionMatch match = iterator.next();

        TranscriptEntry entry;
        entry.startTime = match.captured(1);
        entry.endTime = match.captured(2);
        entry.text = match.captured(3).trimmed();
        entry.startSeconds = timestampToSeconds(entry.startTime);

        if (!entry.text.isEmpty()) {
            entries.append(entry);
        }
    }

    return entries;
}

int TextProcessor::timestampToSeconds(const QString &timestamp)
{
    QStringList parts = timestamp.split(':');

    if (parts.size() == 2) {
        return parts[0].toInt() * 60 + parts[1].toInt();
    } else if (parts.size() == 3) {
        return parts[0].toInt() * 3600 + parts[1].toInt() * 60 + parts[2].toInt();
    }

    return 0;
}

QStringList TextProcessor::createChunks(const QString &text, int maxTokens)
{
    QStringList sentences = splitIntoSentences(text);
    QStringList chunks;
    QString currentChunk;

    for (const QString &sentence : sentences) {
        QString potentialChunk = currentChunk.isEmpty() ? sentence : currentChunk + " " + sentence;

        if (countTokens(potentialChunk) <= maxTokens) {
            currentChunk = potentialChunk;
        } else {
            if (!currentChunk.isEmpty()) {
                chunks.append(currentChunk.trimmed());
            }

            currentChunk = sentence;
        }
    }

    if (!currentChunk.isEmpty()) {
        chunks.append(currentChunk.trimmed());
    }

    QStringList overlappedChunks;
    for (int i = 0; i < chunks.size(); ++i) {
        QString chunk = chunks[i];

        if (i > 0) {
            QStringList prevSentences = splitIntoSentences(chunks[i-1]);
            if (prevSentences.size() >= 2) {
                QString overlap = prevSentences.takeLast() + " " + prevSentences.takeLast();
                chunk = overlap + " " + chunk;
            }
        }

        overlappedChunks.append(chunk);
    }

    return overlappedChunks;
}

QStringList TextProcessor::splitIntoSentences(const QString &text)
{
    QRegularExpression sentenceRegex(R"((?<=[.!?])\s+)");
    QStringList sentences = text.split(sentenceRegex, Qt::SkipEmptyParts);

    QStringList cleanSentences;
    for (const QString &sentence : sentences) {
        QString cleaned = sentence.trimmed();
        if (!cleaned.isEmpty()) {
            cleanSentences.append(cleaned);
        }
    }

    return cleanSentences;
}

int TextProcessor::countTokens(const QString &text)
{
    return text.length() / 4;
}
