# 🎬 Kairozen Video Translator Bot

Bot Telegram សម្រាប់ **ស្តាប់ video/audio + សម្រាយជា​ភាសា​ខ្មែរ + TTS**

| Stack | Tool |
|-------|------|
| Telegram | pyTelegramBotAPI |
| Speech-to-Text | Groq Whisper-large-v3-turbo |
| AI Summary | Groq Llama-3.3-70b |
| TTS | edge-tts (SreymomNeural / PisethNeural) |
| Download | yt-dlp + ffmpeg |

---

## ⚙️ Setup (Server / VPS)

### 1. Clone & Config

```bash
git clone https://github.com/YOUR_USERNAME/kairozen-video-bot.git
cd kairozen-video-bot

cp .env.example .env
nano .env   # បំពេញ BOT_TOKEN, GROQ_API_KEY, ADMIN_ID
```

### 2. Install Dependencies

```bash
# Ubuntu/Debian — install ffmpeg
sudo apt update && sudo apt install -y ffmpeg

# Python venv
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Run

```bash
python bot.py
```

---

## 🐳 Docker

```bash
docker build -t kairozen-video-bot .

docker run -d \
  --name kairozen-video-bot \
  --restart unless-stopped \
  -e BOT_TOKEN=xxx \
  -e GROQ_API_KEY=xxx \
  -e ADMIN_ID=xxx \
  kairozen-video-bot
```

---

## 🔄 Auto-restart (systemd)

```bash
sudo nano /etc/systemd/system/kairozen-video-bot.service
```

```ini
[Unit]
Description=Kairozen Video Translator Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/kairozen-video-bot
EnvironmentFile=/home/ubuntu/kairozen-video-bot/.env
ExecStart=/home/ubuntu/kairozen-video-bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable kairozen-video-bot
sudo systemctl start kairozen-video-bot

# ពិនិត្យ status
sudo systemctl status kairozen-video-bot
sudo journalctl -u kairozen-video-bot -f
```

---

## 🌐 Platforms

| Platform | ដំណើរការ | ចំណាំ |
|----------|----------|--------|
| VPS (Ubuntu) | ✅ | ល្អបំផុត |
| Railway.app | ✅ | Free tier + Docker |
| Render.com | ✅ | Free tier |
| Termux (Android) | ✅ | Dev/test |
| Koyeb | ✅ | Free tier |

---

## 🔑 API Keys

- **BOT_TOKEN** → [@BotFather](https://t.me/BotFather)
- **GROQ_API_KEY** → [console.groq.com](https://console.groq.com)
- **ADMIN_ID** → [@userinfobot](https://t.me/userinfobot)

---

## 📁 Project Structure

```
kairozen-video-bot/
├── bot.py            # Main bot logic
├── config.py         # Load env variables
├── requirements.txt  # Python packages
├── Dockerfile        # Docker build
├── .env.example      # ENV template
├── .gitignore        # Ignore secrets
└── README.md
```

---

> 💬 Support: [@smos_sne1](https://t.me/smos_sne1)
