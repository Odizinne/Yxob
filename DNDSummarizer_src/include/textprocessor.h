#pragma once

#include <QObject>
#include <QString>
#include <QStringList>

struct TranscriptEntry {
    QString participant;
    QString text;
};

class TextProcessor : public QObject
{
    Q_OBJECT

public:
    explicit TextProcessor(QObject *parent = nullptr);

    QString combineTranscripts(const QStringList &filePaths);
    QStringList createChunks(const QString &text, int maxTokens = 2000);
    int countTokens(const QString &text);

private:
    QList<TranscriptEntry> parseTranscriptFile(const QString &filePath);
    QStringList splitIntoSentences(const QString &text);
};
