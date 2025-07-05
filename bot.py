from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import yt_dlp
import os
import whisper
import subprocess
import tempfile
from deep_translator import GoogleTranslator


async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    await update.message.reply_text("📥 Видео юкланмоқда, илтимос кутиб туринг...")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Видео юклаш
            ydl_opts = {
                'outtmpl': f'{tmpdir}/video.%(ext)s',
                'format': 'mp4',
                'quiet': True,
                'noplaylist': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_file = ydl.prepare_filename(info)

            # 2. Whisper модели
            model = whisper.load_model("small")

            # 3. Аудиони матнга айлантириш (автоматик тил аниқлаш)
            result = model.transcribe(video_file)
            segments = result["segments"]
            detected_lang = result["language"]

            # 4. Матнни ўзбекчага таржима қилиш
            for segment in segments:
                orig_text = segment["text"]
                translated = GoogleTranslator(source='auto', target='uz').translate(orig_text)
                segment["text_uz"] = translated

            # 5. .srt файл яратиш
            srt_path = os.path.join(tmpdir, "subs.srt")

            def format_time(seconds):
                h = int(seconds // 3600)
                m = int((seconds % 3600) // 60)
                s = int(seconds % 60)
                ms = int((seconds - int(seconds)) * 1000)
                return f"{h:02}:{m:02}:{s:02},{ms:03}"

            with open(srt_path, "w", encoding="utf-8") as f:
                for i, segment in enumerate(segments, start=1):
                    start = segment["start"]
                    end = segment["end"]
                    text_uz = segment["text_uz"]
                    f.write(f"{i}\n")
                    f.write(f"{format_time(start)} --> {format_time(end)}\n")
                    f.write(text_uz + "\n\n")

            # 6. Видеога субтитрларни ёзиш (hardcode)
            output_video = os.path.join(tmpdir, "video_with_subs.mp4")

            ffmpeg_command = [
                "ffmpeg",
                "-i", video_file,
                "-vf", f"subtitles={srt_path}",
                "-c:a", "copy",
                output_video
            ]

            subprocess.run(ffmpeg_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

            # 7. Юбориш
            await update.message.reply_video(video=open(output_video, 'rb'),
                                             caption="✅ Видео ўзбекча субтитр билан тайёр!")

    except Exception as e:
        await update.message.reply_text(f"❌ Хатолик: {e}")


def main():
    application = Application.builder().token("7230797624:AAE7vX-UeTm_EKEKvHNb07C2rj2_Ft9S8WM").build()

    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), video_handler))

    print("✅ Bot ишга тушди...")
    application.run_polling()


if __name__ == "__main__":
    main()
