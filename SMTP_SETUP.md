# SMTP Configuration

ModelScout can optionally send email notifications after generating a digest.
If SMTP is not configured, digests are still saved locally in the `digests/`
directory.

---

## Prerequisites

Before configuring SMTP, ensure you have:

- A valid email account
- SMTP access enabled
- Internet connectivity
- An App Password (recommended for Gmail)

> **Note**
> Gmail does **not** allow your normal account password.
> Use a Gmail App Password instead.

---

## SMTP Environment Variables

Copy the following values into your `.env` file.

```ini
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

EMAIL_FROM=your-email@gmail.com
EMAIL_TO=recipient@example.com
```

### Variable Reference

| Variable | Description |
|-----------|-------------|
| `SMTP_HOST` | SMTP server hostname |
| `SMTP_PORT` | SMTP server port (587 for TLS) |
| `SMTP_USER` | SMTP login email |
| `SMTP_PASSWORD` | App Password or SMTP password |
| `EMAIL_FROM` | Sender email address |
| `EMAIL_TO` | Recipient email address |

---

## Gmail Setup

1. Open **Google Account → Security**
2. Enable **2-Step Verification**
3. Create an **App Password**
4. Copy the generated password
5. Paste it into `SMTP_PASSWORD`

---

## How It Works

When email is enabled, ModelScout will:

1. Generate the digest
2. Save a Markdown copy in `./digests`
3. Send the same digest via SMTP

If email delivery fails, the local Markdown file is still preserved.

---

## Running

Start the API:

```bash
python app.py
```

Send a request:

```bash
curl -X POST http://127.0.0.1:8015/ask \
-H "Content-Type: application/json" \
-d "{\"prompt\":\"Any new text-generation models today?\"}"
```

Email is sent automatically whenever the agent produces a digest with
something genuinely new to report — there's no separate flag to opt in.

---

## Troubleshooting

### Authentication failed

- Use a Gmail **App Password**
- Verify `SMTP_USER`
- Confirm 2-Step Verification is enabled

### Connection refused

- Verify `SMTP_HOST`
- Verify `SMTP_PORT=587`
- Check firewall or VPN restrictions

### Email not received

- Check the spam folder
- Confirm `EMAIL_TO`
- Verify the application reports **Email sent**

---

## Notes

- SMTP is optional.
- Digests are **always saved locally**, even if email is disabled or delivery fails.
- Gmail, Outlook, and any SMTP-compatible provider are supported.