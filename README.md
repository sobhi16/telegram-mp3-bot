# Telegram MP3 Bot

بوت بسيط: ترسل له رابط فيديو، فيستخرج الصوت ويحوله إلى MP3 ثم يعيد إرسال الملف في نفس محادثة Telegram.

> استخدم التنزيل فقط للمحتوى الذي تملك حق تنزيله أو يسمح لك بتنزيله.

## المتطلبات
- Python 3.11+
- FFmpeg
- Telegram Bot Token

## المتغيرات
```env
TELEGRAM_BOT_TOKEN=...
OWNER_TELEGRAM_ID=...
```

`OWNER_TELEGRAM_ID` اختياري، لكنه مستحسن حتى يبقى البوت خاصًا بك.

## التشغيل
```bash
pip install -r requirements.txt
python bot.py
```

## الاستخدام
1. افتح البوت واضغط Start.
2. أرسل رابط فيديو.
3. انتظر التحويل.
4. يستلم نفس الشات ملف MP3.
