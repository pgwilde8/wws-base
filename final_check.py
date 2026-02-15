import smtplib
from email.message import EmailMessage

# --- HARDCODED CREDENTIALS FOR TESTING ONLY ---
HOST = "fusion.mxrouting.net"
PORT = 465
USER = "dispatch@gcdloads.com"
PASS = "1@NqEfg#^gaVsX1&"  # Ensure this is the EXACT password from Fusion
TO = "techsmartmarketing8@gmail.com"

def test_send():
    print(f"🔄 Attempting to log into {HOST} as {USER}...")
    msg = EmailMessage()
    msg.set_content("This is a hardcoded test to bypass .env issues.")
    msg['Subject'] = "Manual Debug Test"
    msg['From'] = f"seth+TEST123@{USER.split('@')[1]}"
    msg['To'] = TO

    try:
        with smtplib.SMTP_SSL(HOST, PORT, timeout=10) as smtp:
            print("📡 Connection established. Logging in...")
            smtp.login(USER, PASS)
            print("🔑 Login successful! Sending message...")
            smtp.send_message(msg)
            print("✅ Message sent successfully!")
    except smtplib.SMTPAuthenticationError:
        print("❌ FAILED: Authentication Error. Check your username/password.")
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")

if __name__ == "__main__":
    test_send()