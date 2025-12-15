# NOTE: USE ONLY SPACES (4 PER INDENT)

from telethon import TelegramClient, events, Button
import os, re, hashlib, csv
from datetime import datetime

# ================= CONFIG =================
api_id = 34958210
api_hash = "6923cd2c34591c8e26b30ade39c7518b"        # PUT API HASH
bot_token = "8302113399:AAFtZbJNUeKHKTajY21JvKe8k_Mf46KX0xg"       # PUT BOT TOKEN
ADMIN_ID = 6860983540

PASSKEY = "SPIDYWS"
PASSKEY_HASH = hashlib.sha256(PASSKEY.encode()).hexdigest()

# ================= INIT =================
client = TelegramClient("spidy_vcf_bot", api_id, api_hash).start(bot_token=bot_token)

user_sessions = {}
user_state = {}
user_files = {}
user_data = {}

# ================= HELPERS =================
def init_user(uid):
    user_state.setdefault(uid, "MENU")
    user_files.setdefault(uid, [])
    user_data.setdefault(uid, {})

def cleanup(uid):
    for f in user_files.get(uid, []):
        try:
            if os.path.exists(f):
                os.remove(f)
        except:
            pass
    user_files[uid] = []
    user_state[uid] = "MENU"
    user_data[uid] = {}

def split_name_number(text):
    m = re.match(r"(.*?)(\d+)?$", text)
    base = m.group(1)
    start = int(m.group(2)) if m.group(2) else 1
    return base, start

async def log_user(event):
    user = await event.get_sender()
    msg = (
        "👤 BOT USER\n\n"
        f"ID: {user.id}\n"
        f"Username: @{user.username}\n"
        f"Name: {user.first_name} {user.last_name}\n"
        f"Time: {datetime.now()}"
    )
    await client.send_message(ADMIN_ID, msg)

async def show_menu(chat):
    await client.send_message(
        chat,
        "👇 Choose option",
        buttons=[
            [Button.inline("🧑🏻‍🔧 EDIT VCF", b"edit")],
            [Button.inline("🔪 SPLIT VCF", b"split")],
            [Button.inline("🧪 ADVANCE VCF EDITOR", b"advance")]
        ]
    )

# ================= START =================
@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    uid = event.sender_id
    if uid not in user_sessions:
        await log_user(event)
        await event.reply("🔐 Send passkey")
    else:
        await show_menu(event.chat_id)

# ================= MAIN HANDLER =================
@client.on(events.NewMessage)
async def handler(event):
    uid = event.sender_id
    chat = event.chat_id
    text = (event.raw_text or "").strip()
    init_user(uid)

    # ---------- PASSKEY ----------
    if uid not in user_sessions:
        if hashlib.sha256(text.encode()).hexdigest() == PASSKEY_HASH:
            user_sessions[uid] = True
            await log_user(event)
            await event.reply("✅ Access granted")
            await show_menu(chat)
        else:
            await event.reply("❌ Wrong passkey")
        return

    state = user_state[uid]

    # ---------- FILE RECEIVE ----------
    if event.file:
        path = f"{uid}_{event.file.name}"
        await event.download_media(path)
        user_files[uid].append(path)
        await event.reply("📥 File received\n➡️ Send /done")
        return

    # ---------- EDIT VCF ----------
    if state == "WAIT_VCF_BASE":
        base, start = split_name_number(text)
        user_data[uid]["vcf_base"] = base
        user_data[uid]["vcf_start"] = start
        user_state[uid] = "WAIT_CONTACT_BASE"
        await event.reply("👤 Send base CONTACT name (Spidy01)")
        return

    if state == "WAIT_CONTACT_BASE":
        cname_base, cname_start = split_name_number(text)
        vbase = user_data[uid]["vcf_base"]
        vstart = user_data[uid]["vcf_start"]
        counter = cname_start

        for i, src in enumerate(user_files[uid]):
            out = f"{vbase}{vstart + i:02}.vcf"
            with open(src, "r", errors="ignore") as r:
                cards = r.read().split("END:VCARD")

            with open(out, "w") as w:
                for card in cards:
                    if "BEGIN:VCARD" not in card:
                        continue
                    name = f"{cname_base}{counter:02}"
                    counter += 1
                    w.write("BEGIN:VCARD\n")
                    for line in card.splitlines():
                        if line.startswith("FN:"):
                            w.write(f"FN:{name}\n")
                        elif line.startswith("N:"):
                            w.write(f"N:{name};;;;\n")
                        elif not line.startswith("BEGIN:VCARD"):
                            w.write(line + "\n")
                    w.write("END:VCARD\n")

            await client.send_file(chat, out)
            os.remove(out)

        cleanup(uid)
        await show_menu(chat)
        return

    # ---------- SPLIT VCF ----------
    if state == "WAIT_SPLIT_COUNT":
        count = int(text)
        src = user_files[uid][0]
        with open(src, "r", errors="ignore") as r:
            cards = [c for c in r.read().split("END:VCARD") if "BEGIN:VCARD" in c]

        for i in range(0, len(cards), count):
            out = f"split_{i//count + 1}.vcf"
            with open(out, "w") as w:
                for c in cards[i:i + count]:
                    w.write(c.strip() + "\nEND:VCARD\n")
            await client.send_file(chat, out)
            os.remove(out)

        cleanup(uid)
        await show_menu(chat)
        return

    # ---------- MAKE VCF ----------
    if state == "WAIT_MAKE_NUMBERS":
        out = "numbers.vcf"
        with open(out, "w") as w:
            for i, n in enumerate(text.splitlines(), 1):
                if n.strip().isdigit():
                    w.write(
                        "BEGIN:VCARD\nVERSION:3.0\n"
                        f"N:Contact{i};;;;\nFN:Contact{i}\nTEL:{n}\nEND:VCARD\n"
                    )
        await client.send_file(chat, out)
        os.remove(out)
        cleanup(uid)
        await show_menu(chat)
        return

    # ---------- ADD NUMBERS ----------
    if state == "WAIT_ADDNUM_NUMBERS":
        src = user_files[uid][0]
        out = "added_numbers.vcf"
        with open(src, "r", errors="ignore") as r:
            data = r.read()
        with open(out, "w") as w:
            w.write(data)
            for i, n in enumerate(text.splitlines(), 1):
                if n.strip().isdigit():
                    w.write(
                        "BEGIN:VCARD\nVERSION:3.0\n"
                        f"N:New{i};;;;\nFN:New{i}\nTEL:{n}\nEND:VCARD\n"
                    )
        await client.send_file(chat, out)
        os.remove(out)
        cleanup(uid)
        await show_menu(chat)
        return

    # ---------- TXT TO VCF ----------
    if state == "WAIT_TXT_FILE":
        src = user_files[uid][0]
        out = "txt_to_vcf.vcf"
        with open(src, "r", errors="ignore") as r, open(out, "w") as w:
            for i, n in enumerate(r, 1):
                if n.strip().isdigit():
                    w.write(
                        "BEGIN:VCARD\nVERSION:3.0\n"
                        f"N:Contact{i};;;;\nFN:Contact{i}\nTEL:{n.strip()}\nEND:VCARD\n"
                    )
        await client.send_file(chat, out)
        os.remove(out)
        cleanup(uid)
        await show_menu(chat)
        return

    # ---------- CSV TO VCF ----------
    if state == "WAIT_CSV_FILE":
        src = user_files[uid][0]
        out = "csv_to_vcf.vcf"
        with open(src, encoding="utf-8") as f, open(out, "w") as w:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2 and row[1].strip().isdigit():
                    w.write(
                        "BEGIN:VCARD\nVERSION:3.0\n"
                        f"N:{row[0]};;;;\nFN:{row[0]}\nTEL:{row[1]}\nEND:VCARD\n"
                    )
        await client.send_file(chat, out)
        os.remove(out)
        cleanup(uid)
        await show_menu(chat)
        return

    # ---------- VCF TO TXT (NEW) ----------
    if state == "WAIT_VCF_TO_TXT":
        out = "vcf_to_txt.txt"
        numbers = []
        for fpath in user_files[uid]:
            with open(fpath, "r", errors="ignore") as r:
                for line in r:
                    if line.startswith("TEL:"):
                        numbers.append(line.replace("TEL:", "").strip())
        with open(out, "w") as w:
            w.write("\n".join(numbers))
        await client.send_file(chat, out)
        os.remove(out)
        cleanup(uid)
        await show_menu(chat)
        return

# ================= BUTTONS =================
@client.on(events.CallbackQuery)
async def buttons(event):
    uid = event.sender_id
    init_user(uid)

    if event.data == b"edit":
        user_files[uid] = []
        user_state[uid] = "WAIT_EDIT_FILES"
        await event.reply("📤 Upload VCF files\n➡️ Send /done")

    elif event.data == b"split":
        user_files[uid] = []
        user_state[uid] = "WAIT_SPLIT_FILES"
        await event.reply("📤 Upload ONE VCF file\n➡️ Send /done")

    elif event.data == b"advance":
        await event.reply(
            "🧪 ADVANCE VCF EDITOR",
            buttons=[
                [Button.inline("🔗 MERGE VCF", b"merge")],
                [Button.inline("➕ ADD NUMBERS", b"addnum")],
                [Button.inline("📇 MAKE VCF", b"makevcf")],
                [Button.inline("♻️ TXT TO VCF", b"txt2vcf")],
                [Button.inline("♻️ CSV TO VCF", b"csv2vcf")],
                [Button.inline("♻️ VCF TO TXT", b"vcftotxt")]
            ]
        )

    elif event.data == b"merge":
        user_files[uid] = []
        user_state[uid] = "WAIT_MERGE"
        await event.reply("📤 Upload VCF files\n➡️ Send /done")

    elif event.data == b"addnum":
        user_files[uid] = []
        user_state[uid] = "WAIT_ADDNUM_FILE"
        await event.reply("📤 Upload ONE VCF file\n➡️ Send /done")

    elif event.data == b"makevcf":
        user_state[uid] = "WAIT_MAKE_NUMBERS"
        await event.reply("📱 Send phone numbers")

    elif event.data == b"txt2vcf":
        user_files[uid] = []
        user_state[uid] = "WAIT_TXT_FILE"
        await event.reply("📄 Upload TXT file\n➡️ Send /done")

    elif event.data == b"csv2vcf":
        user_files[uid] = []
        user_state[uid] = "WAIT_CSV_FILE"
        await event.reply("📊 Upload CSV file\n➡️ Send /done")

    elif event.data == b"vcftotxt":
        user_files[uid] = []
        user_state[uid] = "WAIT_VCF_TO_TXT"
        await event.reply("📤 Upload VCF files\n➡️ Send /done")

# ================= DONE =================
@client.on(events.NewMessage(pattern="/done"))
async def done(event):
    uid = event.sender_id

    if user_state.get(uid) == "WAIT_EDIT_FILES":
        user_state[uid] = "WAIT_VCF_BASE"
        await event.reply("📝 Send BASE VCF file name")

    elif user_state.get(uid) == "WAIT_SPLIT_FILES":
        user_state[uid] = "WAIT_SPLIT_COUNT"
        await event.reply("🔢 Send contacts per file")

    elif user_state.get(uid) == "WAIT_MERGE":
        out = "merged.vcf"
        with open(out, "w") as w:
            for f in user_files[uid]:
                with open(f, "r", errors="ignore") as r:
                    w.write(r.read())
        await client.send_file(event.chat_id, out)
        os.remove(out)
        cleanup(uid)
        await show_menu(event.chat_id)

    elif user_state.get(uid) == "WAIT_ADDNUM_FILE":
        user_state[uid] = "WAIT_ADDNUM_NUMBERS"
        await event.reply("📱 Send numbers")

    elif user_state.get(uid) in ["WAIT_TXT_FILE", "WAIT_CSV_FILE", "WAIT_VCF_TO_TXT"]:
        # For these states, /done triggers processing
        await handler(event)

# ================= RUN =================
print("🤖 Bot running...")
client.run_until_disconnected()