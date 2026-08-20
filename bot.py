import asyncio
import os
import re
import shutil
import tempfile
import random
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import yt_dlp


load_dotenv()


# =========================
# إعدادات البوت
# =========================

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

OWNER_TELEGRAM_ID = os.getenv("OWNER_TELEGRAM_ID")
OWNER_TELEGRAM_ID = (
    int(OWNER_TELEGRAM_ID)
    if OWNER_TELEGRAM_ID
    else None
)

# عنوان خدمة PO Token Provider على Railway
POT_PROVIDER_URL = os.getenv(
    "YTDLP_POT_PROVIDER_URL",
    "http://bgutil-ytdlp-pot-provider.railway.internal:4416",
)


# =========================
# رسائل صبحي الروبوت 😂
# =========================

WORKING_MESSAGES = [
    "ثواني… قاعد أعصر الفيديو عشان أطلعلك الصوت 😭",
    "اصبر عليّ، مش شايفني بشتغل؟ 😂",
    "جاري ارتكاب بعض الأمور التقنية… 🧑‍💻",
    "دخل الرابط غرفة العمليات 🏥",
    "استنى… الـFFmpeg قاعد يسخن 😂",
    "جاري تحويل ذوقك الموسيقي إلى ملف قابل للحفظ 🎧",
    "ثواني بس، السيرفر عنده مشاعر برضو.",
    "بفكك الفيديو قطعة قطعة… هو تحت التخدير.",
]


SUCCESS_MESSAGES = [
    "في كمان أغاني؟ 👀",
    "خلصت هاي، هات المصيبة اللي بعدها 😂",
    "تم يا زعيم. مين الضحية الجاية؟",
    "هات اللي بعدها… واضح السهرة مطوّلة 🎧",
    "MP3 جاهز. رأيي بالأغنية احتفظت فيه لنفسي احترامًا لمشاعرك.",
    "خلصت. لا تقلي عندك Playlist كاملة 💀",
    "تمت المهمة بنجاح. إنجاز آخر يُحسب للحضارة البشرية.",
    "هات رابط ثاني، السيرفر دافع حقه.",
    "واحدة راحت… كم باقي عندك يا طمّاع؟ 😭",
    "تم 🫡 صبحي الروبوت لا يسأل لماذا، صبحي الروبوت ينفّذ.",
    "خلصت يا DJ، شو التالية؟",
    "جاهزة. الشكر مش ضروري، التحويل الجاي بكفي.",
    "الله يسامح اللي علّمك تبعتلي روابط 😂",
    "تم. أنا حرفيًا موظف عندك بدون راتب.",
    "هاي كمان خلصت… ما عندك Spotify يزم؟ 😭",
]


ERROR_MESSAGES = [
    "الرابط قرر يقاوم 💀",
    "هذا الرابط بيني وبينه مشاكل شخصية.",
    "حتى أنا عندي حدود يزم، هات رابط ثاني 😭",
    "الرابط مات قبل وصوله إلى المستشفى.",
    "فشلت العملية… أهل الفيديو رفضوا التبرع بالصوت.",
    "يا الرابط خربان، يا أنا بحاجة إجازة. جرّب واحد ثاني 😂",
]


# =========================
# أدوات مساعدة
# =========================

def owner_only(update: Update) -> bool:
    if OWNER_TELEGRAM_ID is None:
        return True

    return bool(
        update.effective_user
        and update.effective_user.id == OWNER_TELEGRAM_ID
    )


def extract_url(text: str):
    match = re.search(r"https?://\S+", text or "")

    if not match:
        return None

    return match.group(0).rstrip(").,]}>")


# =========================
# تنزيل وتحويل MP3
# =========================

def download_mp3(url: str, workdir: Path) -> Path:

    outtmpl = str(
        workdir / "%(title).120s [%(id)s].%(ext)s"
    )

    opts = {

        # أفضل صوت متوفر
        "format": "bestaudio/best",

        "outtmpl": outtmpl,

        # لا نريد Playlist كاملة بالغلط 😂
        "noplaylist": True,

        "quiet": True,

        # خليه يظهر تحذيرات مهمة في Railway
        "no_warnings": False,

        # =====================
        # YouTube + PO Token
        # =====================

        "extractor_args": {

            "youtube": {

                # العميل الموصى به للـPO Token
                "player_client": [
                    "mweb"
                ],

                # اجبر yt-dlp يطلب PO Token
                "fetch_pot": [
                    "always"
                ],

                # يظهر معلومات PO Token في Logs
                "pot_trace": [
                    "true"
                ],

                # يسمح برؤية الصيغ التي تعتمد على POT
                "formats": [
                    "missing_pot"
                ],
            },

            # Plugin الخاص بخدمة bgutil
            "youtubepot-bgutilhttp": {

                "base_url": [
                    POT_PROVIDER_URL
                ],
            },
        },

        # =====================
        # تحويل الصوت
        # =====================

        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    with yt_dlp.YoutubeDL(opts) as ydl:

        info = ydl.extract_info(
            url,
            download=True,
        )

        original_file = Path(
            ydl.prepare_filename(info)
        )

        mp3_path = original_file.with_suffix(
            ".mp3"
        )

    # احتياط إذا اسم الملف تغيّر بعد FFmpeg
    if not mp3_path.exists():

        candidates = list(
            workdir.glob("*.mp3")
        )

        if not candidates:

            raise FileNotFoundError(
                "لم يتم العثور على ملف MP3 بعد التحويل."
            )

        mp3_path = candidates[0]

    return mp3_path


# =========================
# /start
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not owner_only(update):

        await update.message.reply_text(
            "هذا البوت خاص 😎"
        )

        return

    await update.message.reply_text(
        "شبيك لبيك، صبحي الروبوت بين إيديك 🧞‍♂️🎧\n\n"
        "إيش بدنا ننزّل اليوم؟ أغاني؟ 👀\n"
        "ارمي الرابط وخلّي الباقي عليّ."
    )


# =========================
# /myid
# =========================

async def myid(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        f"Telegram ID: {update.effective_user.id}"
    )


# =========================
# استقبال الرابط
# =========================

async def handle_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not owner_only(update):

        await update.message.reply_text(
            "هذا البوت خاص 😎"
        )

        return

    url = extract_url(
        update.message.text or ""
    )

    if not url:

        await update.message.reply_text(
            "وين الرابط يا زعيم؟ 😭\n"
            "ارمي رابط فيديو وخليني أشتغل."
        )

        return


    status = await update.message.reply_text(
        random.choice(
            WORKING_MESSAGES
        )
    )


    try:

        with tempfile.TemporaryDirectory(
            prefix="tg_mp3_"
        ) as td:

            workdir = Path(td)

            mp3 = await asyncio.to_thread(
                download_mp3,
                url,
                workdir,
            )


            size_mb = (
                mp3.stat().st_size
                / (1024 * 1024)
            )


            if size_mb > 49:

                await status.edit_text(
                    f"يا ساتر 😭 الملف طلع {size_mb:.1f}MB.\n"
                    "أكبر من اللي بقدر أبعثه حاليًا."
                )

                return


            await status.edit_text(
                "خلصنا التشريح 🫡\n"
                "هسا برفعلك الـMP3…"
            )


            with mp3.open("rb") as audio:

                await update.message.reply_audio(

                    audio=audio,

                    title=mp3.stem[:64],

                    caption="تفضل يا فنان 🎧",
                )


        # نمسح رسالة جاري التحويل
        await status.delete()


        # رد مضحك عشوائي
        await update.message.reply_text(
            random.choice(
                SUCCESS_MESSAGES
            )
        )


        # 5% احتمال يطلع الرد النقابي 😂
        if random.random() < 0.05:

            await update.message.reply_text(
                "بالمناسبة… كم أغنية ناوي تنزّل؟ "
                "أنا بس بسأل لأسباب نقابية."
            )


    except Exception as e:

        funny_error = random.choice(
            ERROR_MESSAGES
        )

        await status.edit_text(
            f"{funny_error}\n\n"
            f"المشكلة التقنية: "
            f"{type(e).__name__}"
        )


# =========================
# تشغيل البوت
# =========================

def main():

    if shutil.which("ffmpeg") is None:

        raise RuntimeError(
            "FFmpeg غير مثبت على الخادم."
        )


    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )


    app.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )


    app.add_handler(
        CommandHandler(
            "myid",
            myid,
        )
    )


    app.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            handle_text,
        )
    )


    print(
        "صبحي الروبوت شغّال 😎"
    )

    print(
        f"PO Provider: {POT_PROVIDER_URL}"
    )


    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
