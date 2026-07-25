from send_email import send_email

result = send_email(
    subject="Pipeline Test",
    body="Your sports pipeline email is configured correctly.\n\nTesting 1-2-3."
)

if result:
    print("Email working!")
else:
    print("Check your Gmail App Password in email_config.py")
