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

        // Extract participant name from filename
        QFileInfo fileInfo(filePath);
        QString fileName = fileInfo.baseName();
        QStringList parts = fileName.split('_');
        QString participant = parts.isEmpty() ? fileName : parts.last();

        if (!participants.contains(participant)) {
            participants.append(participant);
        }

        // Add participant info to entries
        for (auto &entry : entries) {
            entry.participant = participant;
            allEntries.append(entry);
        }
    }

    // Sort by timestamp
    std::sort(allEntries.begin(), allEntries.end(),
              [](const TranscriptEntry &a, const TranscriptEntry &b) {
                  return a.startSeconds < b.startSeconds;
              });

    // Create combined transcript
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

    // Parse timestamp entries: [MM:SS -> MM:SS] text
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
        // MM:SS format
        return parts[0].toInt() * 60 + parts[1].toInt();
    } else if (parts.size() == 3) {
        // HH:MM:SS format
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
            // Current chunk is full, start a new one
            if (!currentChunk.isEmpty()) {
                chunks.append(currentChunk.trimmed());
            }

            // If single sentence is too long, include it anyway
            currentChunk = sentence;
        }
    }

    // Add the last chunk
    if (!currentChunk.isEmpty()) {
        chunks.append(currentChunk.trimmed());
    }

    // Add overlap between chunks for context continuity
    QStringList overlappedChunks;
    for (int i = 0; i < chunks.size(); ++i) {
        QString chunk = chunks[i];

        if (i > 0) {
            // Add some sentences from previous chunk for context
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
    // Enhanced sentence splitting for French
    QRegularExpression sentenceRegex(R"((?<=[.!?])\s+)");
    QStringList sentences = text.split(sentenceRegex, Qt::SkipEmptyParts);

    // Clean up sentences
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
    // Rough token count estimation (1 token ≈ 4 characters)
    return text.length() / 4;
}
