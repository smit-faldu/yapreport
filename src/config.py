import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# API Keys
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

# Reference Audio & Text
TRUMP_REF_AUDIO = os.path.join(BASE_DIR, "assets", "new trump.wav")
TRUMP_REF_TEXT  = "Well, thank you very much, Larry. It's great to be back in beautiful Davos, Switzerland, and to address so many respected business leaders, so many friends, few enemies [laughing] and all of the distinguished"

ELON_REF_AUDIO  = os.path.join(BASE_DIR, "assets", "new elon.wav")
ELON_REF_TEXT   = "Okay, sure. Yes, um, I am Elon Musk, the CEO of Tesla and SpaceX, and previously of PayPal, but I sold that for $100 million and reinvested everything into where I am now. And my, my latest project"

# Audio Settings
PAUSE_SEC          = 0.0   
OUTPUT_SCRIPT_PATH = "todays_script.json"
OUTPUT_AUDIO_PATH  = "todays_podcast.wav"
OMNIVOICE_SR       = 24000

# Video settings
BG_VIDEO_PATH = os.path.join(BASE_DIR, "assets", "minecraft_loop.mp4")
TRUMP_IMG     = os.path.join(BASE_DIR, "assets", "trump.png")
ELON_IMG      = os.path.join(BASE_DIR, "assets", "elon.png")
OUTPUT_VIDEO_PATH = "final_short.mp4"

# Canvas
W, H = 1080, 1920
FPS  = 30

# Caption design
FONT_SIZE      = 75
WORDS_PER_CAP  = 3
CAPTION_Y      = int(H * 0.50)
C_WHITE        = (255, 255, 255, 255)
C_GREEN        = (0, 255, 0,   255)
C_STROKE       = (0,   0,   0,   255)
STROKE_W       = 5

# Portrait design
PHOTO_SIZE     = 650
PHOTO_X        = (W - PHOTO_SIZE) // 2
PHOTO_Y        = H - PHOTO_SIZE - 50

# WhisperX and Fonts
WHISPER_MODEL  = "base"
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
FONT_PATH = os.path.join(FONTS_DIR, "LuckiestGuy-Regular.ttf")
FONT_URL  = "https://github.com/google/fonts/raw/main/apache/luckiestguy/LuckiestGuy-Regular.ttf"
