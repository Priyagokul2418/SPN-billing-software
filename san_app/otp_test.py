import smtplib
from email.mime.text import MIMEText

def quick_test():
    try:
        print("Testing Vallibricks SMTP...")
        
        smtp_server = "mail.vallibricks.com"
        port = 465
        username = "spn@vallibricks.com"
        password = "spnVallibricks@123"  # ⚠️ PUT YOUR PASSWORD HERE
        to_email = "priyagokul854@gmail.com"
        
        # Simple message
        msg = MIMEText("This is a test email from vallibricks.com")
        msg['Subject'] = 'Test Email'
        msg['From'] = username
        msg['To'] = to_email
        
        # Connect and send
        with smtplib.SMTP_SSL(smtp_server, port) as server:
            server.set_debuglevel(1)
            server.login(username, password)
            server.sendmail(username, to_email, msg.as_string())
        
        print("✓ Email sent successfully!")
        
    except Exception as e:
        print(f"✗ Failed: {e}")

quick_test()