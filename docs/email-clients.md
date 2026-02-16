Email Clients
Configuration settings for setting up your email in desktop and mobile apps.

Contact Form
The contact form sends submissions to contact@gcdloads.com. Add this to .env:

```
# Contact form recipient (create this mailbox in MXRoute)
CONTACT_RECIPIENT_EMAIL=contact@gcdloads.com

# SMTP to send (same as broker emails - dispatch@gcdloads.com)
MXROUTE_SMTP_HOST=fusion.mxrouting.net
MXROUTE_SMTP_PORT=465
MXROUTE_SMTP_USER=dispatch@gcdloads.com
MXROUTE_SMTP_PASSWORD=your-password
```

Create contact@gcdloads.com as a mailbox in MXRoute so you receive form submissions.

Webmail no DNS required
fusion.mxrouting.net/webmail
Webmail requires MX records
mail.mxlogin.com
webmail.mxroute.com
Account Settings
Use these settings when configuring your email client:

Username
your-full-email@address.com
Use your complete email address
Password
Your email account password
The password you set when creating the email account
Server Hostname
fusion.mxrouting.net

Use for IMAP, POP3, and SMTP servers
IMAP Settings
Recommended for most users
IMAP syncs your email across all devices. Changes made on one device appear on all others.

Connection Type	Port	Encryption
Secure Recommended	993	SSL/TLS
Standard	143	STARTTLS
POP3 Settings
POP3 downloads email to a single device. Messages are typically removed from the server after download.

Connection Type	Port	Encryption
Secure Recommended	995	SSL/TLS
Standard	110	STARTTLS
SMTP Settings
Outgoing Mail
SMTP is used for sending outgoing email. Most email clients will auto-detect these settings.

Connection Type	Port	Encryption
Secure Recommended	465	SSL/TLS
Submission	587	STARTTLS
Alternative	2525	STARTTLS
Standard Not Recommended	25	None
Tip: If port 465 or 587 is blocked by your ISP, try port 2525 as an alternative.

Quick Reference
Copy these recommended settings for quick setup:

Incoming Mail (IMAP)
Server: fusion.mxrouting.net
Port: 993
Security: SSL/TLS
Outgoing Mail (SMTP)
Server: fusion.mxrouting.net
Port: 465
Security: SSL/TLS