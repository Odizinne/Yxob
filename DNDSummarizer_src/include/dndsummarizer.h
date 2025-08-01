#pragma once

#include <QObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include "textprocessor.h"

class DnDSummarizer : public QObject
{
    Q_OBJECT

public:
    explicit DnDSummarizer(QObject *parent = nullptr);

    void summarizeFiles(const QStringList &filePaths);
    void setCustomPrompts(const QString &chunkPrompt, const QString &finalPrompt);

signals:
    void summaryReady(const QString &summary);
    void errorOccurred(const QString &error);
    void progressUpdated(const QString &status);

private slots:
    void onSummaryRequestFinished();

private:
    void processNextChunk();
    QString createPrompt(const QString &text, bool isFinalSummary);
    QString getDefaultChunkPrompt() const;
    QString getDefaultFinalPrompt() const;

    QNetworkAccessManager* m_networkManager;
    TextProcessor* m_textProcessor;

    QStringList m_chunkSummaries;
    QStringList m_remainingChunks;
    int m_totalChunks;
    int m_currentChunk;

    QString m_customChunkPrompt;
    QString m_customFinalPrompt;
};
