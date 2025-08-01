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

    for (const QString &filePath : std::as_const(filePaths)) {
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

    QString combined = QString("Session D&D avec %1\n").arg(participants.join(", "));
    combined += QString("=").repeated(50) + "\n\n";

    for (const auto &entry : std::as_const(allEntries)) {
        combined += QString("%1: %2\n\n").arg(entry.participant, entry.text);
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
    QStringList lines = content.split('\n');
    bool foundSeparator = false;

    for (const QString &line : std::as_const(lines)) {
        if (!foundSeparator) {
            if (line.startsWith("=")) {
                foundSeparator = true;
            }
            continue;
        }

        QString trimmedLine = line.trimmed();
        if (!trimmedLine.isEmpty()) {
            TranscriptEntry entry;
            entry.text = trimmedLine;
            entries.append(entry);
        }
    }

    return entries;
}

QStringList TextProcessor::createChunks(const QString &text, int maxTokens)
{
    QStringList sentences = splitIntoSentences(text);
    QStringList chunks;
    QString currentChunk;

    for (const QString &sentence : std::as_const(sentences)) {
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
    static const QRegularExpression sentenceRegex(R"((?<=[.!?])\s+)");
    QStringList sentences = text.split(sentenceRegex, Qt::SkipEmptyParts);

    QStringList cleanSentences;
    for (const QString &sentence : std::as_const(sentences)) {
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
