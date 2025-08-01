import asyncio
import whisper
import os
from datetime import datetime
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
            from discord_recorder import bot
            asyncio.run_coroutine_threadsafe(bot.close(), self.loop)

            self.wait(2000)
            if self.isRunning():
                self.terminate()


class TranscriptionWorker(QThread):
    progress = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, files_to_transcribe, base_recordings_dir):
        super().__init__()
        self.files_to_transcribe = files_to_transcribe
        self.base_recordings_dir = base_recordings_dir

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
    
                # Determine the correct transcripts directory based on the file location
                file_dir = os.path.dirname(wav_file)
                if file_dir == self.base_recordings_dir:
                    # File is in root recordings directory
                    transcripts_dir = os.path.join(self.base_recordings_dir, "transcripts")
                else:
                    # File is in a date subdirectory
                    transcripts_dir = os.path.join(file_dir, "transcripts")
                
                os.makedirs(transcripts_dir, exist_ok=True)
    
                base_name = os.path.splitext(os.path.basename(wav_file))[0]
                transcript_file = os.path.join(transcripts_dir, f"{base_name}.txt")
    
                with open(transcript_file, "w", encoding="utf-8") as f:
                    f.write(f"Transcript for: {os.path.basename(wav_file)}\n")
                    f.write("=" * 50 + "\n\n")
    
                    for segment in result["segments"]:
                        text = segment["text"].strip()
                        f.write(f"{text}\n")
    
                print(f"Transcript saved: {transcript_file}")
    
            self.progress.emit(f"Completed transcription of {total_files} files")
            self.finished.emit()
    
        except Exception as e:
            self.error.emit(f"Transcription error: {str(e)}")