import os
import subprocess
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Render-এর Environment Variable থেকে টোকেন গ্রহণ
TOKEN = os.getenv("8768229210:AAFZRrhz89j5KJNV5CF9eZbe4I8hEpt8mBA")

# টোকেন লোড হয়েছে কি না তা যাচাইকরণ
if not TOKEN:
    raise ValueError("ERROR: BOT_TOKEN পাওয়া যায়নি! Render-এর Environment Settings চেক করুন।")


# Render Health Check-এর জন্য Dummy HTTP Server
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running successfully!")

def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()


# /start কমান্ড হ্যান্ডলার
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "স্বাগতম! আমাকে একটি ভিডিও পাঠান।\n"
        "তারপর Full Screen বা Half Screen সিলেক্ট করে ভিডিও এডিট করতে পারবেন।"
    )


# ইউজার ভিডিও পাঠালে হ্যান্ডেল করার ফাংশন
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    video_file = await message.video.get_file()
    
    # ইনপুট ও আউটপুট ফোল্ডার তৈরি
    os.makedirs("input", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    input_path = "input/v.mp4"
    await video_file.download_to_drive(input_path)

    # Inline Keyboard Buttons তৈরি
    keyboard = [
        [
            InlineKeyboardButton("🎬 Full Screen", callback_data="fullscreen"),
            InlineKeyboardButton("🖼️ Half Screen", callback_data="halfscreen"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text("ভিডিও পাওয়া গেছে! কোন মোডে এডিট করতে চান সিলেক্ট করুন:", reply_markup=reply_markup)


# বাটনে ক্লিক করলে এডিটিং রান করার ফাংশন
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    mode = query.data
    await query.edit_message_text(text=f"⏳ প্রসেসিং শুরু হয়েছে ({mode.upper()} মোড)... অনুগ্রহ করে অপেক্ষা করুন।")

    input_file = "input/v.mp4"
    
    if mode == "fullscreen":
        output_file = "output/Full_Screen_Output.mp4"
        cmd = (
            f"ffmpeg -y -i {input_file} "
            f"-ss 4 -i {input_file} "
            '-filter_complex "[0:v]scale=iw:ih[v2];[1:v]crop=in_w/2:in_h/2:(in_w-out_w)/2+((in_w-out_w)/2)*sin(t*0.5):(in_h-out_h)/2 +((in_h-out_h)/2)*sin(t*0.2),boxblur=1:1,scale=iw*2:ih*2[v1];[v2][v1]overlay=1:enable=\'gte(mod(t,5),3)\':x=0:y=0;[0:a]atempo=1,bass=frequency=200:gain=-90,volume=+20dB,aecho=1:0.6:2:0.4,bass=g=3:f=110:w=20,bass=g=10:f=500:w=20,bass=g=3:f=300:w=30,bass=g=10:f=110:w=20,bass=g=20:f=110:w=40,firequalizer=gain_entry=\'entry(0,-23);entry(250,-11.5);entry(6000,0);entry(12000,8);entry(16000,16)\',compand=attacks=7:decays=1:points=-90/-90 -70/-60 -15/-15 0/-10:soft-knee=1:volume=-70:gain=3,pan=stereo| FL < FL + 0.5*FC + 0.6*BL + 0.6*SL | FR < FR + 2*FC + 1*BR + 2*SR,highpass=f=300,lowpass=f=700,volume=6[a1];amovie=bg2.mp4:loop=9999,volume=1[a2];[a1][a2]amix=duration=shortest" '
            "-vcodec libx264 -pix_fmt yuv420p -r 30 -g 60 -b:v 1550k -shortest -acodec aac -b:a 128k -ar 44100 "
            '-threads 0 -preset ultrafast -crf 30 '
            f'"{output_file}"'
        )
    elif mode == "halfscreen":
        output_file = "output/Half_Screen_Output.mp4"
        cmd = (
            f"ffmpeg -y -i {input_file} -i blocker.mp4 -i myvideo.mp4 "
            '-filter_complex "[0:v]crop=iw/1.2:ih/1.2, scale=392x315, setpts=PTS/1[v]; movie=ibg.mp4:loop=999,setpts=N/(FRAME_RATE*TB) [bg];[bg][v]overlay=shortest=1:x=2:y=107,setsar=1:1[vmain];[1:v]scale=854x480,setsar=1:1[vblock];[2:v]scale=854x480,setsar=1:1[vgam];[0:a]atempo=1,bass=frequency=200:gain=-90,volume=+20dB,aecho=1:0.6:2:0.4,bass=g=3:f=110:w=20,bass=g=10:f=500:w=20,bass=g=3:f=300:w=30,bass=g=10:f=110:w=20,bass=g=20:f=110:w=40,firequalizer=gain_entry=\'entry(0,-23);entry(250,-11.5);entry(6000,0);entry(12000,8);entry(16000,16)\',compand=attacks=7:decays=1:points=-90/-90-70/-60 -15/-15 0/-10: soft-knee=1:volume=-70:gain=3,pan=stereo| FL < FL + 0.5*FC + 0.6*BL + 0.6*SL | FR < FR + 2*FC + 1*BR + 2*SR,highpass=f=300,lowpass=f=700,volume=6[a1];amovie=bg2.mp4: loop=9999,volume=1[a2];[a1][a2]amix=duration=shortest[amain];[vmain][amain][vblock][1:a][vgam][2:a]concat=n=3:v=1:a=1" '
            "-vcodec libx264 -pix_fmt yuv420p -r 30 -g 60 -b:v 1000k -shortest -acodec aac -b:a 128k -ar 44100 -threads 0 "
            f'"{output_file}"'
        )

    # FFmpeg কমান্ড রান করা
    process = subprocess.run(cmd, shell=True)

    if process.returncode == 0 and os.path.exists(output_file):
        await query.message.reply_text("✅ ভিডিও এডিটিং সম্পন্ন হয়েছে! পাঠানো হচ্ছে...")
        with open(output_file, 'rb') as video:
            await query.message.reply_video(video=video, caption=f"{mode.capitalize()} Screen Successfully Created!")
    else:
        await query.message.reply_text("❌ এডিটিং করার সময় কোনো একটি সমস্যা দেখা দিয়েছে।")


if __name__ == '__main__':
    # బ్యాగ్రౌండ్ ব্যাকগ্রাউন্ডে HTTP సర్వర్ চালু করা
    threading.Thread(target=run_http_server, daemon=True).start()

    # টেলিগ্রাম বট অ্যাপ্লিকেশন সেটআপ
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("Bot is listening for videos...")
    app.run_polling()
