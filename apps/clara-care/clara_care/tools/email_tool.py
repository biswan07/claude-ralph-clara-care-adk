"""Email sender tool for ClaraCare.

This module provides functionality to send emails via SMTP, including support
for attachments and inline images, to handle warranty claim submissions.
"""

import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from clara_care.config import settings

logger = logging.getLogger(__name__)


def send_email(
    to_address: str,
    subject: str,
    body: str,
    cc_address: str | None = None,
    reply_to: str | None = None,
    image_url: str | None = None,
    html_body: str | None = None,
) -> str:
    """
    Send an email via SMTP with optional CC, Reply-To, HTML content, and image.

    Args:
        to_address (str): Recipient email address.
        subject (str): Email subject line.
        body (str): Email body text (plain text).
        cc_address (str, optional): CC recipient email address.
        reply_to (str, optional): Reply-To email address.
        image_url (str, optional): URL of an image to mention or attach.
            Appended to plain text body if provided.
        html_body (str, optional): HTML version of the email body.

    Returns:
        str: JSON string indicating success or failure.
    """
    if not settings.smtp_host or not settings.smtp_username or not settings.smtp_password:
        msg = "SMTP settings not configured. Email sending skipped."
        logger.warning(msg)
        return f'{{"success": false, "message": "{msg}"}}'

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = formataddr(("ClaraCare Support", settings.smtp_from_email or settings.smtp_username))
        msg["To"] = to_address
        
        if cc_address:
            msg["Cc"] = cc_address
        
        if reply_to:
            msg["Reply-To"] = reply_to

        # Append image URL to plain text body if present
        full_body = body
        if image_url:
            full_body += f"\n\n[Attached Receipt Reference]: {image_url}"

        msg.set_content(full_body)
        
        # Add HTML alternative if provided
        if html_body:
            msg.add_alternative(html_body, subtype='html')
        
        # If we wanted to send HTML:
        # msg.add_alternative(full_body_html, subtype='html')

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)

        logger.info(
            f"Email sent successfully to {to_address}, cc={cc_address}, reply_to={reply_to}"
        )
        return '{"success": true, "message": "Email sent successfully"}'

    except Exception as e:
        error_msg = f"Failed to send email: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f'{{"success": false, "message": "{error_msg}"}}'
