import asyncio
import whisper
import os
from PySide6.QtCore import QThread, Signal
from discord.ext import commands


class AsyncWorker(QThread):
    def __init__(self, recorder):
        super().__init__()
        self.recorder = recorder
        self.loop = None
        self.should_stop = False

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            self.loop.run_until_complete(self.recorder._run_bot())
        except Exception as e:
            print(f"Bot error: {e}")
        finally:
            self.loop.close()

    def stop(self):
        self.should_stop = True
        if self.loop and not self.loop.is_closed():
            # Import bot from discord_recorder to avoid circular import
            from discord_recorder import bot
            asyncio.run_coroutine_threadsafe(bot.close(), self.loop)

            self.wait(2000)
            if self.isRunning():
                self.terminate()


class TranscriptionWorker(QThread):
    progress = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, files_to_transcribe, recordings_dir):
        super().__init__()
        self.files_to_transcribe = files_to_transcribe
        self.recordings_dir = recordings_dir
        self.transcripts_dir = os.path.join(recordings_dir, "transcripts")
        os.makedirs(self.transcripts_dir, exist_ok=True)

    def run(self):
        try:
            self.progress.emit("Loading Whisper model...")
            model = whisper.load_model("large")

            total_files = len(self.files_to_transcribe)

            for i, wav_file in enumerate(self.files_to_transcribe, 1):
                self.progress.emit(
                    f"Transcribing {os.path.basename(wav_file)} ({i}/{total_files})..."
                )

                result = model.transcribe(wav_file)

                base_name = os.path.splitext(os.path.basename(wav_file))[0]
                transcript_file = os.path.join(self.transcripts_dir, f"{base_name}.txt")

                with open(transcript_file, "w", encoding="utf-8") as f:
                    f.write(f"Transcript for: {os.path.basename(wav_file)}\n")
                    f.write("=" * 50 + "\n\n")

                    for segment in result["segments"]:
                        start_time = self._format_timestamp(segment["start"])
                        end_time = self._format_timestamp(segment["end"])
                        text = segment["text"].strip()

                        f.write(f"[{start_time} -> {end_time}] {text}\n")

                print(f"Transcript saved: {transcript_file}")

            self.progress.emit(f"Completed transcription of {total_files} files")
            self.finished.emit()

        except Exception as e:
            self.error.emit(f"Transcription error: {str(e)}")

    def _format_timestamp(self, seconds):
        """Format timestamp as HH:MM:SS.mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
        else:
            return f"{minutes:02d}:{secs:06.3f}"