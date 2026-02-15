import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Add the parent directory to sys.path to allow imports from clara_care
# This assumes the script is located in apps/clara-care/scripts/
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from clara_care.config import settings
    from clara_care.tools.email_tool import send_email
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you are running this script from the correct environment.")
    sys.exit(1)

def test_email():
    print("Testing Email Configuration...")
    print(f"SMTP Host: {settings.smtp_host}")
    print(f"SMTP Port: {settings.smtp_port}")
    print(f"SMTP Username: {settings.smtp_username}")
    # Mask password for security
    masked_password = "*****" if settings.smtp_password else "None"
    print(f"SMTP Password: {masked_password}")
    print(f"From Email: {settings.smtp_from_email}")

    if not settings.smtp_host:
        print("Error: SMTP_HOST not set in environment or .env file.")
        return

    # Default to sending to the configured username/from_email if available, 
    # otherwise ask the user or fail
    recipient = settings.smtp_username or settings.smtp_from_email
    
    if not recipient:
        print("Error: Could not determine recipient. Please ensure SMTP_USERNAME or SMTP_FROM_EMAIL is set.")
        return

    subject = "Test Email from ClaraCare Agent"
    body = "This is a test email to verify the SMTP configuration for the ClaraCare agent."

    print(f"\nSending test email to: {recipient}")
    
    try:
        result = send_email(to_address=recipient, subject=subject, body=body)
        print(f"Result: {result}")
    except Exception as e:
        print(f"An error occurred while sending email: {e}")

if __name__ == "__main__":
    test_email()
