"""
Welcome Email Service - Sends beta driver welcome emails with Discord buyback feed info.
"""
from app.services.email import MXROUTE_SMTP_HOST, MXROUTE_SMTP_PORT, MXROUTE_SMTP_USER, MXROUTE_SMTP_PASSWORD, MXROUTE_FROM_EMAIL
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os


def send_welcome_email_to_driver(
    driver_email: str,
    driver_name: str,
    dashboard_url: str = None,
    discord_invite_url: str = None
) -> dict:
    """
    Send welcome email to new beta driver explaining:
    - How the AI negotiation flow works
    - The PENDING_APPROVAL → CONFIRM safety check
    - How to watch the live buyback feed on Discord
    """
    if not MXROUTE_SMTP_USER or not MXROUTE_SMTP_PASSWORD:
        return {
            "status": "error",
            "message": "mxroute SMTP not configured"
        }
    
    dashboard_url = dashboard_url or os.getenv("BASE_URL", "https://greencandledispatch.com")
    discord_invite_url = discord_invite_url or os.getenv("DISCORD_INVITE_URL", "https://discord.gg/greencandle")
    
    # Load HTML template
    from jinja2 import Environment, FileSystemLoader
    import os
    template_dir = os.path.join(os.path.dirname(__file__), "..", "templates", "emails")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("welcome_beta_driver.html")
    
    html_content = template.render(
        driver_name=driver_name,
        dashboard_url=dashboard_url,
        discord_invite_url=discord_invite_url
    )
    
    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg['From'] = MXROUTE_FROM_EMAIL
        msg['To'] = driver_email
        msg['Subject'] = "🕯️ Welcome to Green Candle Dispatch - Beta Fleet"
        
        # Plain text version (fallback)
        text_content = f"""
Welcome to Green Candle Dispatch, {driver_name}!

You're now part of the Beta Fleet. Your AI dispatch agent is live and ready to negotiate loads.

WHAT HAPPENS NEXT:
1. AI negotiates → Your agent drafts emails to brokers asking for better rates
2. Broker replies → When they say "yes" with a rate, you'll get a notification
3. You confirm → Review the rate and click CONFIRM (or reject if something looks off)
4. Load secured → Once you confirm, 2.5% goes to the $CANDLE buyback pool

WATCH THE LIVE BUYBACK FEED:
Join our Discord to see every load win, every buyback trigger, every driver contribution in real-time:
{discord_invite_url}
Channel: #buyback-feed

YOUR DASHBOARD:
{dashboard_url}

Questions? Hit reply or join our Discord.

Let's build the future of freight together,
The Green Candle Team
"""
        
        part1 = MIMEText(text_content, "plain")
        part2 = MIMEText(html_content, "html")
        
        msg.attach(part1)
        msg.attach(part2)
        
        # Send via mxroute SMTP
        with smtplib.SMTP(MXROUTE_SMTP_HOST, MXROUTE_SMTP_PORT) as server:
            server.starttls()
            server.login(MXROUTE_SMTP_USER, MXROUTE_SMTP_PASSWORD)
            server.send_message(msg)
        
        return {
            "status": "success",
            "message": f"Welcome email sent to {driver_email}"
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to send welcome email: {str(e)}"
        }
