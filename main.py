import os
import re
import math
import asyncio
import subprocess
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from telethon import TelegramClient, events, Button

# -------------------------------------------------------------------
# আপনার তথ্যগুলো সরাসরি এখানে বসান:
TOKEN = "8768229210:AAFZRrhz89j5KJNV5CF9eZbe4I8hEpt8mBA"          # যেমন: "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"
API_ID = 32537921                          # আপনার api_id (কোনো " " চিহ্ন ছাড়া শুধুমাত্র সংখ্যা)
API_HASH = "5000ba0c58c228dece1daf8c3aaee83d"        # যেমন: "a1b2c3d4e5f6g7h8i9j0"
# -------------------------------------------------------------------

# Telethon Bot Client ইনিশিয়ালাইজেশন
bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=TOKEN)

# UptimeRobot & Render Health Check HTTP Server
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot is running with Big File Support!")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

def run_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()


# GoFile-এ বড় ফাইল আপলোডের ফাংশন
def upload_to_gofile(file_path):
    try:
        server_resp = requests.get("https://api.gofile.io/servers").json()
        server = server_resp["data"]["servers"][0]["name"] if server_resp.get("status") == "ok" else "store1"

        upload_url = f"https://{server}.gofile.io/contents/uploadfile"
        with open(file_path, "rb") as f:
            files = {"file": f}
            response = requests.post(upload_url, files=files).json()

        if response.get("status") == "ok":
            return response["data"]["downloadPage"]
        return None
    except Exception as e:
        print(f"GoFile Error: {e}")
        return None


# ভিডিওর মোট সময় (Duration) বের করার ফাংশন
def get_video_duration(input_file):
    try:
        cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{input_file}"'
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return float(result.stdout.strip())
    except Exception:
        return 0.0


# /start কমান্ড
@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    await event.respond(
        "স্বাগতম! আমাকে যেকোনো সাইজের (ছোট বা বড়) ভিডিও পাঠান।\n"
        "তারপর Full Screen বা Half Screen সিলেক্ট করে ভিডিও এডিট করতে পারবেন।"
    )


# ভিডিও বা ভিডিও ফাইল রিসিভ করা (বড় ফাইল সাপোর্টসহ)
@bot.on(events.NewMessage)
async def handle_video(event):
    if event.message.video or (event.message.document and event.message.document.mime_type and 'video' in event.message.document.mime_type):
        status_msg = await event.reply("📥 বড় ফাইল ডাউনলোড হচ্ছে... অনুগ্রহ করে অপেক্ষা করুন।")
        
        os.makedirs("input", exist_ok=True)
        os.makedirs("output", exist_ok=True)
        input_path = "input/v.mp4"

        # Telethon Client API দিয়ে যেকোনো আকারের ভিডিও ডাউনলোড
        await event.message.download_media(file=input_path)
        
        buttons = [
            [Button.inline("🎬 Full Screen", data=b"fullscreen"), Button.inline("🖼️ Half Screen", data=b"halfscreen")]
        ]
        await status_msg.edit("✅ ভিডিও ডাউনলোড সম্পন্ন! কোন মোডে এডিট করতে চান সিলেক্ট করুন:", buttons=buttons)


# বাটন ক্লিক ও লাইভ প্রোগ্রেস প্রসেসিং
@bot.on(events.CallbackQuery)
async def button_callback(event):
    mode = event.data.decode('utf-8')
    status_msg = await event.edit(f"⏳ এডিটিং প্রসেস শুরু হচ্ছে ({mode.upper()})... 0%")

    input_file = "input/v.mp4"
    total_duration = get_video_duration(input_file)

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

    process = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE, universal_newlines=True)
    
    last_percent = -1
    for line in process.stderr:
        if "time=" in line and total_duration > 0:
            match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
            if match:
                hours, minutes, seconds = map(float, match.groups())
                current_time = hours * 3600 + minutes * 60 + seconds
                percent = min(100, math.floor((current_time / total_duration) * 100))
                
                if percent >= last_percent + 10:
                    last_percent = percent
                    try:
                        await status_msg.edit(f"⏳ এডিটিং চলছে ({mode.upper()}): {percent}% সম্পন্ন...")
                    except Exception:
                        pass

    process.wait()

    if process.returncode == 0 and os.path.exists(output_file):
        file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
        
        if file_size_mb > 20:
            await status_msg.edit("📤 ভিডিওটি ২০ MB-র বেশি হওয়ায় GoFile-এ আপলোড করা হচ্ছে...")
            download_link = upload_to_gofile(output_file)
            if download_link:
                await event.respond(f"✅ আপনার এডিট করা ভিডিও তৈরি!\n\n🔗 **Download Link:** {download_link}")
            else:
                await event.respond("❌ GoFile-এ আপলোড করতে সমস্যা হয়েছে।")
        else:
            await status_msg.edit("✅ এডিটিং সম্পন্ন! ভিডিও পাঠানো হচ্ছে...")
            await bot.send_file(event.chat_id, output_file, caption=f"{mode.capitalize()} Screen Successfully Created!")
    else:
        await status_msg.edit("❌ এডিটিং করার সময় সমস্যা দেখা দিয়েছে।")


if __name__ == '__main__':
    threading.Thread(target=run_http_server, daemon=True).start()
    print("Bot with Big File capability starting...")
    bot.run_until_disconnected()
