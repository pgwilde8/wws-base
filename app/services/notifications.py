"""
Notifications Service: Onboarding comms (SMS + Email) after Stripe checkout.
"""
import os
from typing import Optional

BASE_URL = os.getenv("BASE_URL", "https://greencandledispatch.com")
LOGIN_URL = os.getenv("LOGIN_URL", f"{BASE_URL}/login/client")


def send_onboarding_comms(
    driver_email: str,
    driver_name: str,
    mc_number: str,
    dispatch_email: str,
    starter_credits: float = 10.0,
    phone: Optional[str] = None,
) -> dict:
    """
    Triggered immediately after onboard_new_driver() succeeds.
    Sends welcome email (dispatch identity + usage menu) and optional SMS.
    Returns: {"email": "success"|"error", "sms": "success"|"skipped"|"error"}
    """
    result = {"email": "error", "sms": "skipped"}

    # 1. Send welcome email
    try:
        from jinja2 import Environment, FileSystemLoader
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        import smtplib

        from app.services.email import (
            MXROUTE_SMTP_HOST as MX_HOST,
            MXROUTE_SMTP_PORT as MX_PORT,
            MXROUTE_SMTP_USER as MX_USER,
            MXROUTE_SMTP_PASSWORD as MX_PASS,
            MXROUTE_FROM_EMAIL,
        )

        template_dir = os.path.join(os.path.dirname(__file__), "..", "templates", "emails")
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template("welcome_onboarding.html")
        html_content = template.render(
            driver_name=driver_name,
            mc_number=mc_number,
            dispatch_email=dispatch_email,
            starter_credits=starter_credits,
            login_url=LOGIN_URL,
        )

        msg = MIMEMultipart("alternative")
        msg["From"] = MXROUTE_FROM_EMAIL or "noreply@greencandledispatch.com"
        msg["To"] = driver_email
        msg["Subject"] = f"Your GCD Identity is Live – {int(starter_credits)} $CANDLE Ready"
        text_fallback = (
            f"Welcome, {driver_name}! Your dispatch identity {dispatch_email} is active. "
            f"We've loaded {starter_credits} $CANDLE into your tank. Login: {LOGIN_URL}"
        )
        msg.attach(MIMEText(text_fallback, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        if MX_USER and MX_PASS:
            with smtplib.SMTP(MX_HOST, MX_PORT) as server:
                server.starttls()
                server.login(MX_USER, MX_PASS)
                server.send_message(msg)
            result["email"] = "success"
    except Exception as e:
        print(f"Onboarding email error: {e}")
        result["email"] = "error"

    # 2. Send SMS (Twilio stub – implement when ready)
    if phone and phone.strip():
        sms_body = (
            f"Welcome to the Fleet, {driver_name}! Your Dispatch Identity {dispatch_email} is active. "
            f"We've loaded {starter_credits} $CANDLE into your tank. Login: {LOGIN_URL}"
        )
        # TODO: Twilio integration
        # from twilio.rest import Client; client.messages.create(...)
        result["sms"] = "skipped"  # Change to "success" when Twilio wired

    return result