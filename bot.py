import asyncio
import os
import random
import re
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

OWNER_TELEGRAM_ID = os.getenv("OWNER_TELEGRAM_ID")
OWNER_TELEGRAM_ID = (
    int(OWNER_TELEGRAM_ID)
    if OWNER_TELEGRAM_ID
    else None
)

Y2MATE_URL = "https://y2mate.gs"


WORKING_MESSAGES = [
    "ثواني… قاعد أعصر الفيديو عشان أطلعلك الصوت 😭",
    "اصبر عليّ، مش شايفني بشتغل؟ 😂",
    "جاري ارتكاب بعض الأمور التقنية… 🧑‍💻",
    "دخل الرابط غرفة العمليات 🏥",
    "ثواني… صبحي الروبوت بلّش المناوبة.",
    "جاري تحويل ذوقك الموسيقي إلى ملف قابل للحفظ 🎧",
    "ثواني بس، السيرفر عنده مشاعر برضو.",
    "بفكك الفيديو قطعة قطعة… هو تحت التخدير.",
]

SUCCESS_MESSAGES = [
    "في كمان أغاني؟ 👀",
    "خلصت هاي، هات المصيبة اللي بعدها 😂",
    "تم يا زعيم. مين الضحية الجاية؟",
    "هات اللي بعدها… واضح السهرة مطوّلة 🎧",
    "رأيي بالأغنية احتفظت فيه لنفسي احترامًا لمشاعرك.",
    "خلصت. لا تقلي عندك Playlist كاملة 💀",
    "إنجاز آخر يُحسب للحضارة البشرية.",
    "هات رابط ثاني، السيرفر دافع حقه.",
    "واحدة راحت… كم باقي عندك يا طمّاع؟ 😭",
    "صبحي الروبوت لا يسأل لماذا، صبحي الروبوت ينفّذ 🫡",
    "خلصت يا DJ، شو التالية؟",
    "الشكر مش ضروري، التحويل الجاي بكفي.",
    "الله يسامح اللي علّمك تبعتلي روابط 😂",
    "أنا حرفيًا موظف عندك بدون راتب.",
    "هاي كمان خلصت… ما عندك Spotify يزم؟ 😭",
]

ERROR_MESSAGES = [
    "الرابط قرر يقاوم 💀",
    "هذا الرابط بيني وبينه مشاكل شخصية.",
    "حتى أنا عندي حدود يزم 😭",
    "الرابط مات قبل وصوله إلى المستشفى.",
    "فشلت العملية… أهل الفيديو رفضوا التبرع بالصوت.",
    "يا الرابط خربان، يا أنا بحاجة إجازة 😂",
]


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


def convert_with_y2mate(video_url: str, workdir: Path) -> Path:

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        context = browser.new_context(
            accept_downloads=True,
            viewport={
                "width": 1280,
                "height": 900,
            },
        )

        page = context.new_page()

        try:

            # افتح Y2Mate
            page.goto(
                Y2MATE_URL,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            # خانة رابط YouTube
            textbox = page.get_by_role("textbox").first

            textbox.wait_for(
                state="visible",
                timeout=30000,
            )

            textbox.fill(video_url)

            # اختر MP3
            mp3_button = page.get_by_role(
                "button",
                name="MP3",
                exact=True,
            )

            if mp3_button.count() > 0:
                mp3_button.first.click()

            # Convert
            convert_button = page.get_by_role(
                "button",
                name="Convert",
                exact=True,
            )

            convert_button.click()

            # التحويل قد يأخذ وقت
            page.wait_for_timeout(2000)

            # انتظر Download
            download_element = page.get_by_text(
                "Download",
                exact=True,
            )

            download_element.wait_for(
                state="visible",
                timeout=180000,
            )

            # اضغط وانتظر تنزيل الملف
            with page.expect_download(
                timeout=180000
            ) as download_info:

                download_element.first.click()

            download = download_info.value

            suggested_name = (
                download.suggested_filename
                or "sobhi-download.mp3"
            )

            # تأكد أنه ينتهي بـ mp3
            if not suggested_name.lower().endswith(".mp3"):
                suggested_name += ".mp3"

            destination = (
                workdir / suggested_name
            )

            download.save_as(
                str(destination)
            )

            if not destination.exists():
                raise RuntimeError(
                    "Y2Mate ما رجّع الملف."
                )

            return destination

        finally:
            context.close()
            browser.close()


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


async def myid(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        f"Telegram ID: {update.effective_user.id}"
    )


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
        random.choice(WORKING_MESSAGES)
    )

    try:

        with tempfile.TemporaryDirectory(
            prefix="sobhi_mp3_"
        ) as td:

            workdir = Path(td)

            mp3 = await asyncio.to_thread(
                convert_with_y2mate,
                url,
                workdir,
            )

            size_mb = (
                mp3.stat().st_size
                / 1024
                / 1024
            )

            if size_mb > 49:

                await status.edit_text(
                    f"يا ساتر 😭 الملف طلع "
                    f"{size_mb:.1f}MB.\n"
                    "أكبر من حد الإرسال الحالي."
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

        await status.delete()

        await update.message.reply_text(
            random.choice(
                SUCCESS_MESSAGES
            )
        )

        # 5% احتمال لرسالة نقابية 😂
        if random.random() < 0.05:

            await update.message.reply_text(
                "بالمناسبة… كم أغنية ناوي تنزّل؟ "
                "أنا بس بسأل لأسباب نقابية."
            )

    except Exception as e:

        funny_error = random.choice(
            ERROR_MESSAGES
        )

        print(
            f"Y2Mate error: "
            f"{type(e).__name__}: {e}"
        )

        await status.edit_text(
            f"{funny_error}\n\n"
            f"المشكلة التقنية: "
            f"{type(e).__name__}"
        )


def main():

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
        "صبحي الروبوت شغّال — Y2Mate mode 😎"
    )

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
