# ╔══════════════════════════════════════════════════════════════╗
# ║      Kairozen Video Translator Bot                           ║
# ║  🎬 Video Summarizer + Translator → ខ្មែរ + TTS             ║
# ║  Stack: yt-dlp + Groq Whisper + deep_translator + edge_tts  ║
# ║  Version: 2.0 (Server/GitHub Edition)                        ║
# ╚══════════════════════════════════════════════════════════════╝

import telebot
import os
import threading
import tempfile
import asyncio
import textwrap
import logging

from groq import Groq
from deep_translator import GoogleTranslator
import edge_tts
import yt_dlp

from config import BOT_TOKEN, GROQ_KEY, ADMIN_ID, VOICES

# ══════ Logging ══════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ]
)
log = logging.getLogger(__name__)

# ══════ Init ══════
bot    = telebot.TeleBot(BOT_TOKEN)
client = Groq(api_key=GROQ_KEY)

# user_id → { voice, waiting_link }
sessions = {}

def get_cfg(uid):
    if uid not in sessions:
        sessions[uid] = {"voice": "sreymom", "waiting_link": False}
    return sessions[uid]


# ══════════════════════════════════════════
# KEYBOARDS
# ══════════════════════════════════════════

def main_kb():
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🎬 ផ្ញើ Video/Audio", "🔗 Link YouTube/TikTok")
    kb.row("⚙️ ជ្រើសសំឡេង", "ℹ️ របៀបប្រើ")
    return kb

def voice_kb():
    kb = telebot.types.InlineKeyboardMarkup()
    kb.row(
        telebot.types.InlineKeyboardButton("👩 ស្រីមុំ (SreymomNeural)", callback_data="v_sreymom"),
        telebot.types.InlineKeyboardButton("👨 ពិសិដ្ឋ (PisethNeural)",  callback_data="v_piseth"),
    )
    return kb


# ══════════════════════════════════════════
# AUDIO TOOLS
# ══════════════════════════════════════════

def extract_audio_from_video(video_path: str, out_path: str) -> bool:
    ret = os.system(
        f'ffmpeg -y -i "{video_path}" -vn -ar 16000 -ac 1 '
        f'-b:a 64k "{out_path}" -loglevel quiet'
    )
    return ret == 0


def download_audio_url(url: str, out_path: str):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_path.replace(".mp3", ""),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "64",
        }],
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title    = info.get("title", "Video")
        duration = info.get("duration", 0)
    return title, duration


# ══════════════════════════════════════════
# WHISPER (Groq)
# ══════════════════════════════════════════

def transcribe_audio(audio_path: str) -> str:
    with open(audio_path, "rb") as f:
        data = f.read()
    result = client.audio.transcriptions.create(
        file=(os.path.basename(audio_path), data),
        model="whisper-large-v3-turbo",
        response_format="text",
        language=None,
    )
    text = result if isinstance(result, str) else result.text
    return text.strip()


# ══════════════════════════════════════════
# SUMMARIZE (Groq LLM)
# ══════════════════════════════════════════

def summarize_with_groq(transcript: str) -> str:
    prompt = f"""អ្នកជាជំនួយការវិភាគ video ជំនាញ។
សូម​សម្រាយ​មាតិកា​ខាង​ក្រោម​ជា​ភាសា​ខ្មែរ​ច្បាស់​លាស់:

📌 ចំណុចសំខាន់ (bullet points)
📝 សេចក្តីសង្ខេបខ្លី (២-៣ ប្រយោគ)
💡 គន្លឹះ ឬ ចំណេះដឹងសំខាន់

មាតិកា:
{transcript[:6000]}

ចម្លើយជាភាសាខ្មែរទាំងស្រុង:"""

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
    )
    return resp.choices[0].message.content.strip()


# ══════════════════════════════════════════
# EDGE TTS
# ══════════════════════════════════════════

async def _tts_async(text: str, voice: str, path: str):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(path)

def make_tts(text: str, voice_key: str) -> str:
    voice = VOICES.get(voice_key, VOICES["sreymom"])
    tmp   = tempfile.mktemp(suffix=".mp3")
    asyncio.run(_tts_async(text, voice, tmp))
    return tmp


# ══════════════════════════════════════════
# CORE PROCESSOR
# ══════════════════════════════════════════

def process_audio_file(chat_id, uid, audio_path, title="Video"):
    cfg = get_cfg(uid)
    try:
        msg = bot.send_message(chat_id, "🎙️ *កំពុង​ស្តាប់​សំឡេង...*", parse_mode="Markdown")
        transcript = transcribe_audio(audio_path)

        if not transcript or len(transcript) < 10:
            bot.edit_message_text("❌ មិន​អាច​ស្គាល់​សំឡេង​បាន។ សូម​ព្យាយាម​ម្ដង​ទៀត។",
                                  chat_id, msg.message_id)
            return

        bot.edit_message_text("🤖 *AI កំពុង​វិភាគ​មាតិកា...*", chat_id, msg.message_id,
                              parse_mode="Markdown")
        summary_km = summarize_with_groq(transcript)

        header    = f"🎬 *{title[:60]}*\n\n" if title else "🎬 *សម្រាយ Video*\n\n"
        full_text = header + summary_km

        bot.delete_message(chat_id, msg.message_id)

        if len(full_text) > 4000:
            for part in textwrap.wrap(full_text, 3800):
                bot.send_message(chat_id, part, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, full_text, parse_mode="Markdown")

        tts_msg = bot.send_message(chat_id, "🔊 *កំពុង​បង្កើត​សំឡេង​ខ្មែរ...*",
                                   parse_mode="Markdown")
        voice_key  = cfg.get("voice", "sreymom")
        voice_name = "ស្រីមុំ 👩" if voice_key == "sreymom" else "ពិសិដ្ឋ 👨"

        tts_text = summary_km[:900]
        tts_path = make_tts(tts_text, voice_key)

        bot.delete_message(chat_id, tts_msg.message_id)

        with open(tts_path, "rb") as audio:
            bot.send_voice(chat_id, audio,
                           caption=f"🎤 {voice_name} — *{VOICES[voice_key]}*",
                           parse_mode="Markdown")
        os.remove(tts_path)
        log.info(f"[✅] Processed: {title} | uid={uid}")

    except Exception as e:
        log.error(f"[❌] process_audio_file error: {e}")
        bot.send_message(chat_id, f"⚠️ Error: `{str(e)[:200]}`", parse_mode="Markdown")
    finally:
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception:
            pass


# ══════════════════════════════════════════
# HANDLERS
# ══════════════════════════════════════════

@bot.message_handler(commands=["start"])
def cmd_start(msg):
    uid  = msg.from_user.id
    name = msg.from_user.first_name or "អ្នកប្រើ"
    get_cfg(uid)
    log.info(f"[/start] uid={uid} name={name}")
    bot.send_message(
        msg.chat.id,
        f"🎬 *សួស្តី {name}!*\n\n"
        f"🤖 *Kairozen Video Translator Bot*\n\n"
        f"✅ ផ្ញើ video/audio → *AI ស្តាប់ + សម្រាយ​ជា​ខ្មែរ*\n"
        f"✅ ផ្ញើ link YouTube/TikTok → *ទាញ​ + សម្រាយ*\n"
        f"✅ ទទួល​ *អត្ថបទ​ + សំឡេង TTS ខ្មែរ*\n\n"
        f"🎤 Voices: `km-KH-SreymomNeural` | `km-KH-PisethNeural`\n\n"
        f"📩 ចាប់ផ្តើម​ដោយ​ផ្ញើ video ឬ link!",
        parse_mode="Markdown",
        reply_markup=main_kb()
    )


@bot.message_handler(func=lambda m: m.text == "ℹ️ របៀបប្រើ")
def cmd_help(msg):
    uid = msg.from_user.id
    cfg = get_cfg(uid)
    vn  = "ស្រីមុំ 👩" if cfg["voice"] == "sreymom" else "ពិសិដ្ឋ 👨"
    bot.send_message(
        msg.chat.id,
        "📖 *របៀបប្រើ Kairozen Video Translator*\n\n"
        "1️⃣ ផ្ញើ *video* ឬ *audio* ដោយផ្ទាល់ → bot ដក​សំឡេង + សម្រាយ\n"
        "2️⃣ ចុច *🔗 Link* រួច​បង្អួត Link YouTube/TikTok/FB\n"
        "3️⃣ ជ្រើសសំឡេង *ស្រី* ឬ *ប្រុស* ក្រោម ⚙️\n\n"
        "*ទ្រង់ទ្រាយ​ file ដែល​គាំទ្រ:*\n"
        "🎥 mp4, mov, avi, mkv, webm\n"
        "🎵 mp3, m4a, ogg, wav, flac\n\n"
        f"⚙️ *ការ​កំណត់​បច្ចុប្បន្ន:*\n"
        f"🎤 សំឡេង: {vn}\n"
        f"🧠 Model: Groq Whisper-large-v3-turbo\n"
        f"🤖 AI: Llama-3.3-70b",
        parse_mode="Markdown"
    )


@bot.message_handler(func=lambda m: m.text == "⚙️ ជ្រើសសំឡេង")
def cmd_voice(msg):
    bot.send_message(
        msg.chat.id,
        "🎤 *ជ្រើសសំឡេង TTS ខ្មែរ:*",
        parse_mode="Markdown",
        reply_markup=voice_kb()
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("v_"))
def cb_voice(call):
    uid = call.from_user.id
    key = call.data.replace("v_", "")
    get_cfg(uid)["voice"] = key
    label = "ស្រីមុំ 👩 — `km-KH-SreymomNeural`" if key == "sreymom" \
            else "ពិសិដ្ឋ 👨 — `km-KH-PisethNeural`"
    bot.answer_callback_query(call.id, "✅ បាន​ជ្រើស!")
    bot.edit_message_text(
        f"✅ *សំឡេង: {label}*",
        call.message.chat.id, call.message.message_id,
        parse_mode="Markdown"
    )


@bot.message_handler(func=lambda m: m.text == "🔗 Link YouTube/TikTok")
def cmd_link_prompt(msg):
    uid = msg.from_user.id
    get_cfg(uid)["waiting_link"] = True
    bot.send_message(
        msg.chat.id,
        "🔗 *សូម​បង្អួត Link:*\n\n"
        "គាំទ្រ: YouTube, TikTok, Facebook, Instagram, Twitter, ...\n\n"
        "_(ផ្ញើ link ក្រោម​នេះ)_",
        parse_mode="Markdown"
    )


@bot.message_handler(func=lambda m: m.text and m.text.startswith("http"))
def handle_link(msg):
    uid  = msg.from_user.id
    chat = msg.chat.id
    url  = msg.text.strip()
    get_cfg(uid)["waiting_link"] = False

    bot.send_message(chat, "⏳ *កំពុង​ទាញ video...*", parse_mode="Markdown")

    def run():
        tmp_audio = tempfile.mktemp(suffix=".mp3")
        try:
            title, duration = download_audio_url(url, tmp_audio)
            actual = tmp_audio if os.path.exists(tmp_audio) else tmp_audio + ".mp3"
            if not os.path.exists(actual):
                bot.send_message(chat, "❌ មិន​អាច​ទាញ video បាន។ សូម​ពិនិត្យ link ម្ដង​ទៀត។")
                return
            mins = f"{int(duration)//60}:{int(duration)%60:02d}" if duration else "?"
            bot.send_message(chat, f"✅ *{title[:50]}*\n⏱ រយៈ​ពេល: `{mins}`",
                             parse_mode="Markdown")
            process_audio_file(chat, uid, actual, title)
        except Exception as e:
            bot.send_message(chat, f"⚠️ Error: `{str(e)[:200]}`", parse_mode="Markdown")

    threading.Thread(target=run, daemon=True).start()


@bot.message_handler(content_types=["video", "document"])
def handle_video(msg):
    uid  = msg.from_user.id
    chat = msg.chat.id

    if msg.video:
        file_info = bot.get_file(msg.video.file_id)
        ext = ".mp4"
    elif msg.document:
        fname = msg.document.file_name or ""
        ext = os.path.splitext(fname)[1] or ".mp4"
        allowed = {".mp4", ".mov", ".avi", ".mkv", ".webm",
                   ".mp3", ".m4a", ".ogg", ".wav", ".flac"}
        if ext.lower() not in allowed:
            bot.reply_to(msg, "❌ ទ្រង់ទ្រាយ​មិន​គាំទ្រ។")
            return
        file_info = bot.get_file(msg.document.file_id)
    else:
        return

    size_mb = file_info.file_size / 1024 / 1024 if hasattr(file_info, "file_size") else 0
    if size_mb > 50:
        bot.reply_to(msg, "⚠️ File ធំ​ពេក (>50MB)។ សូម​ប្រើ link ជំនួស​វិញ។")
        return

    bot.send_message(chat, "⬇️ *កំពុង​ទាញ file...*", parse_mode="Markdown")

    def run():
        tmp_video = tempfile.mktemp(suffix=ext)
        tmp_audio = tempfile.mktemp(suffix=".mp3")
        try:
            downloaded = bot.download_file(file_info.file_path)
            with open(tmp_video, "wb") as f:
                f.write(downloaded)

            ok = extract_audio_from_video(tmp_video, tmp_audio)
            if not ok or not os.path.exists(tmp_audio):
                tmp_audio = tmp_video
            title = (msg.video.file_name if msg.video and hasattr(msg.video, "file_name")
                     else (msg.document.file_name if msg.document else "Video")) or "Video"
            process_audio_file(chat, uid, tmp_audio, title)
        except Exception as e:
            bot.send_message(chat, f"⚠️ Error: `{str(e)[:200]}`", parse_mode="Markdown")
        finally:
            for p in [tmp_video]:
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass

    threading.Thread(target=run, daemon=True).start()


@bot.message_handler(content_types=["audio", "voice"])
def handle_audio(msg):
    uid  = msg.from_user.id
    chat = msg.chat.id

    if msg.voice:
        file_info = bot.get_file(msg.voice.file_id)
        ext, title = ".ogg", "Voice Message"
    else:
        file_info = bot.get_file(msg.audio.file_id)
        ext   = os.path.splitext(msg.audio.file_name or "")[1] or ".mp3"
        title = msg.audio.title or msg.audio.file_name or "Audio"

    bot.send_message(chat, "⬇️ *កំពុង​ទាញ​សំឡេង...*", parse_mode="Markdown")

    def run():
        tmp_audio = tempfile.mktemp(suffix=ext)
        try:
            downloaded = bot.download_file(file_info.file_path)
            with open(tmp_audio, "wb") as f:
                f.write(downloaded)
            process_audio_file(chat, uid, tmp_audio, title)
        except Exception as e:
            bot.send_message(chat, f"⚠️ Error: `{str(e)[:200]}`", parse_mode="Markdown")

    threading.Thread(target=run, daemon=True).start()


@bot.message_handler(func=lambda m: m.text and not m.text.startswith("http")
                     and m.text not in ["🎬 ផ្ញើ Video/Audio", "🔗 Link YouTube/TikTok",
                                         "⚙️ ជ្រើសសំឡេង", "ℹ️ របៀបប្រើ"])
def handle_text(msg):
    uid = msg.from_user.id
    if get_cfg(uid).get("waiting_link"):
        bot.reply_to(msg, "⚠️ Link មិន​ត្រឹម​ត្រូវ។ Link ត្រូវ​ចាប់ផ្ដើម​ដោយ `http://` ឬ `https://`",
                     parse_mode="Markdown")
    else:
        bot.reply_to(msg, "📩 សូម​ផ្ញើ *video*, *audio*, ឬ *link* មក!", parse_mode="Markdown")


# ══════════════════════════════════════════
# RUN
# ══════════════════════════════════════════

if __name__ == "__main__":
    log.info("🎬 Kairozen Video Translator Bot started...")
    log.info(f"🎤 Voices: {list(VOICES.values())}")
    bot.infinity_polling(timeout=60, long_polling_timeout=30)
