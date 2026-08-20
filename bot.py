import asyncio
import os
import re
import shutil
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import yt_dlp

load_dotenv()

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
OWNER_TELEGRAM_ID = os.getenv("OWNER_TELEGRAM_ID")
OWNER_TELEGRAM_ID = int(OWNER_TELEGRAM_ID) if OWNER_TELEGRAM_ID else None


def owner_only(update: Update) -> bool:
    if OWNER_TELEGRAM_ID is None:
        return True
    return bool(update.effective_user and update.effective_user.id == OWNER_TELEGRAM_ID)


def extract_url(text: str):
    m = re.search(r"https?://\S+", text or "")
    return m.group(0).rstrip(").,]}>") if m else None


def download_mp3(url: str, workdir: Path) -> Path:
    outtmpl = str(workdir / "%(title).120s [%(id)s].%(ext)s")
    opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        prepared = Path(ydl.prepare_filename(info))
        mp3_path = prepared.with_suffix(".mp3")

    if not mp3_path.exists():
        candidates = list(workdir.glob("*.mp3"))
        if not candidates:
            raise FileNotFoundError("لم يتم العثور على ملف MP3 بعد التحويل.")
        mp3_path = candidates[0]

    return mp3_path


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update):
        await update.message.reply_text("هذا البوت خاص.")
        return

    await update.message.reply_text(
        "جاهز 🎧\n\n"
        "أرسل رابط فيديو، وأنا أحوّله إلى MP3 وأرجعه لك هنا."
    )


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Telegram ID: {update.effective_user.id}")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update):
        await update.message.reply_text("هذا البوت خاص.")
        return

    url = extract_url(update.message.text or "")
    if not url:
        await update.message.reply_text("أرسل رابط فيديو صالح.")
        return

    status = await update.message.reply_text("جاري استخراج الصوت وتحويله إلى MP3…")

    try:
        with tempfile.TemporaryDirectory(prefix="tg_mp3_") as td:
            workdir = Path(td)
            mp3 = await asyncio.to_thread(download_mp3, url, workdir)

            size_mb = mp3.stat().st_size / (1024 * 1024)
            if size_mb > 49:
                await status.edit_text(
                    f"الملف الناتج حجمه حوالي {size_mb:.1f}MB وهو أكبر من حد الإرسال العملي الحالي للبوت."
                )
                return

            await status.edit_text("تم التحويل، جاري رفع الملف…")
            with mp3.open("rb") as audio:
                await update.message.reply_audio(
                    audio=audio,
                    title=mp3.stem[:64],
                    caption="MP3 جاهز 🎧",
                )

        await status.delete()

    except Exception as e:
        await status.edit_text(f"تعذر التحويل:\n{type(e).__name__}: {e}")


def main():
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("FFmpeg غير مثبت على الخادم.")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Telegram MP3 bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
