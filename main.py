import os
import json
import logging
from datetime import datetime, timezone
import base64
import mimetypes
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import gspread
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from google.oauth2.service_account import Credentials
from pydantic import BaseModel, EmailStr, field_validator
from fastapi.exceptions import RequestValidationError

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# ── Load .env ────────────────────────────────────────────────────────────────
load_dotenv()

SHEET_ID = os.getenv("SHEET_ID")
SERVICE_ACCOUNT_JSON = os.getenv("SERVICE_ACCOUNT_JSON")  # JSON string of credentials

# ── SMTP Settings ────────────────────────────────────────────────────────────
SYSTEM_SENDER_EMAIL = os.getenv("SYSTEM_SENDER_EMAIL")
SYSTEM_ALERT_RECEIVER = os.getenv("SYSTEM_ALERT_RECEIVER")
SYSTEM_SMTP_PASSWORD = os.getenv("SYSTEM_SMTP_PASSWORD")
SYSTEM_SMTP_HOST = os.getenv("SYSTEM_SMTP_HOST", "smtp.gmail.com")
SYSTEM_SMTP_PORT_STR = os.getenv("SYSTEM_SMTP_PORT", "587")
try:
    SYSTEM_SMTP_PORT = int(SYSTEM_SMTP_PORT_STR)
except (ValueError, TypeError):
    SYSTEM_SMTP_PORT = 587

MOCK_MODE = False
sheet = None
creds = None

if not SHEET_ID or not SERVICE_ACCOUNT_JSON:
    log.warning("⚠️ SHEET_ID or SERVICE_ACCOUNT_JSON not set in .env. Running in LOCAL MOCK MODE.")
    MOCK_MODE = True
else:
    # ── Google Sheets client (initialised once at startup) ───────────────────────
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
    ]

    try:
        creds_dict = json.loads(SERVICE_ACCOUNT_JSON)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(SHEET_ID).sheet1          # First tab
        log.info("✅  Google Sheets connected — Sheet ID: %s", SHEET_ID)

        # Write header row if the sheet is empty
        if sheet.row_count == 0 or not sheet.row_values(1):
            sheet.append_row([
                "Timestamp (UTC)",
                "First Name",
                "Last Name",
                "Full Name",
                "Email",
                "Phone",
                "Company",
                "Designation",
                "Service",
                "Message",
                "Attachment"
            ], value_input_option="USER_ENTERED")
            log.info("Header row written to sheet.")

    except Exception as e:
        log.error("Failed to initialise Google Sheets client: %s. Falling back to LOCAL MOCK MODE.", e)
        MOCK_MODE = True

# ── FastAPI app ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Autonomiqa Contact Form API",
    description="Receives contact form submissions and appends them to Google Sheets.",
    version="1.0.0",
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    errors = exc.errors()
    # Pydantic v2 includes ValueError objects in the 'ctx' dict, which makes it non-serializable.
    # We strip out the non-serializable objects from 'ctx' or just convert them to strings.
    serializable_errors = []
    for err in errors:
        err_copy = dict(err)
        if "ctx" in err_copy:
            ctx_copy = {}
            for k, v in err_copy["ctx"].items():
                if isinstance(v, Exception):
                    ctx_copy[k] = str(v)
                else:
                    ctx_copy[k] = v
            err_copy["ctx"] = ctx_copy
        serializable_errors.append(err_copy)

    log.error("Validation error for request: %s", serializable_errors)
    return JSONResponse(
        status_code=422,
        content={"detail": serializable_errors},
    )

DEFAULT_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5500",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5500",
    "http://127.0.0.1:8000",
    "https://autonomiqa.co",
    "null",
    "*"
]

allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

if not allowed_origins:
    allowed_origins = DEFAULT_ORIGINS

# Allow requests from local React dev server and the deployed website
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request schema ────────────────────────────────────────────────────────────
class ContactPayload(BaseModel):
    name: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    designation: Optional[str] = None
    company: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    service: Optional[str] = None
    message: str
    fileData: Optional[str] = None  # Base64 string data URI
    fileName: Optional[str] = None

    @field_validator("name", "firstName", "lastName", "designation", "company", "phone", "service", mode="before")
    @classmethod
    def clean_empty_strings(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v == "":
                return None
        return v

    @field_validator("name")
    @classmethod
    def name_validation(cls, v: str) -> str:
        if v is not None:
            v = v.strip()
            if len(v) < 2:
                raise ValueError("Name must be at least 2 characters.")
        return v

    @field_validator("firstName")
    @classmethod
    def first_name_validation(cls, v: str) -> str:
        if v is not None:
            v = v.strip()
            if len(v) < 2:
                raise ValueError("First name must be at least 2 characters.")
        return v

    @field_validator("lastName")
    @classmethod
    def last_name_validation(cls, v: str) -> str:
        if v is not None:
            v = v.strip()
            if len(v) < 2:
                raise ValueError("Last name must be at least 2 characters.")
        return v

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Message must be at least 10 characters.")
        return v


def process_file_upload(file_data_str: str, file_name: str) -> str:
    """
    Decodes a base64 data URL and saves/uploads it.
    Returns the file path or Google Drive link.
    """
    if not file_data_str:
        return ""

    try:
        # file_data_str looks like: "data:application/pdf;base64,JVBERi0xLj..."
        if "," in file_data_str:
            header, base64_str = file_data_str.split(",", 1)
        else:
            base64_str = file_data_str
            header = ""

        # Decode base64 bytes
        file_bytes = base64.b64decode(base64_str)

        # Get MIME type
        mime_type = "application/octet-stream"
        if "data:" in header and ";base64" in header:
            mime_type = header.split(";base64")[0].replace("data:", "")

        if MOCK_MODE:
            # Save locally
            uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
            os.makedirs(uploads_dir, exist_ok=True)
            local_path = os.path.join(uploads_dir, file_name)
            with open(local_path, "wb") as f:
                f.write(file_bytes)
            log.info("✅ [MOCK] File saved locally to %s", local_path)
            return f"uploads/{file_name}"
        else:
            # Upload to Google Drive using the service account credentials
            log.info("Uploading file '%s' to Google Drive...", file_name)
            import google.auth.transport.requests
            request = google.auth.transport.requests.Request()
            creds.refresh(request)

            headers = {"Authorization": f"Bearer {creds.token}"}
            metadata = {
                "name": file_name,
            }
            files = {
                'data': ('metadata', json.dumps(metadata), 'application/json; charset=UTF-8'),
                'file': (file_name, file_bytes, mime_type)
            }
            r = requests.post(
                "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
                headers=headers,
                files=files
            )
            r.raise_for_status()
            res_data = r.json()
            file_id = res_data.get("id")

            if not file_id:
                raise ValueError("Did not receive file ID from Google Drive API.")

            # Set permission to anyone with link
            permission_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions"
            requests.post(permission_url, headers=headers, json={
                "role": "reader",
                "type": "anyone"
            }).raise_for_status()

            web_view_link = f"https://drive.google.com/file/d/{file_id}/view?usp=drivesdk"
            log.info("✅ File uploaded to Google Drive: %s", web_view_link)
            return web_view_link

    except Exception as e:
        log.error("Failed to process file upload: %s", e)
        return f"Upload failed: {str(e)}"


def send_smtp_alert(payload: ContactPayload, attachment_url: str = ""):
    """Sends an email notification with the submission details."""
    if not SYSTEM_SENDER_EMAIL or not SYSTEM_ALERT_RECEIVER or not SYSTEM_SMTP_PASSWORD:
        log.warning("⚠️ SMTP settings not fully configured in env. Email alert skipped.")
        return

    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"New Lead Submission: {payload.firstName or ''} {payload.lastName or ''} ({payload.company or 'No Company'})"
        msg["From"] = SYSTEM_SENDER_EMAIL
        msg["To"] = SYSTEM_ALERT_RECEIVER

        # HTML body
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #ddd; padding: 20px; border-radius: 8px;">
                <h2 style="color: #F97316; border-bottom: 2px solid #F97316; padding-bottom: 10px;">New Form Submission Received</h2>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr style="background-color: #f9f9f9;">
                        <td style="padding: 8px; font-weight: bold; width: 150px;">First Name:</td>
                        <td style="padding: 8px;">{payload.firstName or "N/A"}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold;">Last Name:</td>
                        <td style="padding: 8px;">{payload.lastName or "N/A"}</td>
                    </tr>
                    <tr style="background-color: #f9f9f9;">
                        <td style="padding: 8px; font-weight: bold;">Email:</td>
                        <td style="padding: 8px;"><a href="mailto:{payload.email}">{payload.email}</a></td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold;">Phone:</td>
                        <td style="padding: 8px;">{payload.phone or "N/A"}</td>
                    </tr>
                    <tr style="background-color: #f9f9f9;">
                        <td style="padding: 8px; font-weight: bold;">Company:</td>
                        <td style="padding: 8px;">{payload.company or "N/A"}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold;">Designation:</td>
                        <td style="padding: 8px;">{payload.designation or "N/A"}</td>
                    </tr>
                    <tr style="background-color: #f9f9f9;">
                        <td style="padding: 8px; font-weight: bold;">Service Needed:</td>
                        <td style="padding: 8px;">{payload.service or "N/A"}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold;">Attachment:</td>
                        <td style="padding: 8px;">
                            {f'<a href="{attachment_url}" target="_blank">View Uploaded File</a>' if attachment_url else "None"}
                        </td>
                    </tr>
                </table>
                <div style="margin-top: 20px; padding: 15px; background-color: #f5f5f5; border-radius: 4px; border-left: 4px solid #F97316;">
                    <strong style="display: block; margin-bottom: 5px;">Message:</strong>
                    <p style="margin: 0; white-space: pre-wrap;">{payload.message}</p>
                </div>
                <hr style="border: 0; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="font-size: 12px; color: #777; text-align: center;">This is an automated alert sent from your Autonomiqa Website Backend.</p>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_content, "html"))

        # Connect and send
        log.info("Connecting to SMTP server %s:%d...", SYSTEM_SMTP_HOST, SYSTEM_SMTP_PORT)
        
        # Determine whether to use SSL or STARTTLS
        if SYSTEM_SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SYSTEM_SMTP_HOST, SYSTEM_SMTP_PORT)
        else:
            server = smtplib.SMTP(SYSTEM_SMTP_HOST, SYSTEM_SMTP_PORT)
            server.starttls()
            
        server.login(SYSTEM_SENDER_EMAIL, SYSTEM_SMTP_PASSWORD)
        server.sendmail(SYSTEM_SENDER_EMAIL, SYSTEM_ALERT_RECEIVER, msg.as_string())
        server.quit()
        log.info("✅ SMTP alert sent successfully to %s", SYSTEM_ALERT_RECEIVER)
    except Exception as e:
        log.error("Failed to send SMTP alert: %s", e)


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def read_root():
    """Serves the standalone website HTML file."""
    html_path = os.path.join(os.path.dirname(__file__), "Autonomiqa_Website_with_Contact.html")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content, status_code=200)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Website HTML file not found.")


@app.get("/health")
def health():
    """Quick health-check endpoint."""
    return {"status": "ok", "service": "Autonomiqa Contact API"}


@app.post("/submit-form", status_code=201)
def submit_form(payload: ContactPayload):
    """
    Receives contact form data (name, email, message, etc.) and appends it
    as a new row in the configured Google Sheet or stores it locally.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Handle file upload if present
    attachment_url = ""
    if payload.fileData and payload.fileName:
        attachment_url = process_file_upload(payload.fileData, payload.fileName)

    if MOCK_MODE:
        try:
            mock_file = "submissions_mock.json"
            submissions = []
            if os.path.exists(mock_file):
                try:
                    with open(mock_file, "r", encoding="utf-8") as f:
                        submissions = json.load(f)
                except Exception:
                    pass
            
            # Use the combined full name if name is not explicitly passed
            full_name = payload.name or f"{payload.firstName or ''} {payload.lastName or ''}".strip()

            submissions.append({
                "timestamp": timestamp,
                "firstName": payload.firstName,
                "lastName": payload.lastName,
                "name": full_name or None,
                "email": payload.email,
                "phone": payload.phone,
                "company": payload.company,
                "designation": payload.designation,
                "service": payload.service,
                "message": payload.message,
                "attachment": attachment_url or None
            })
            with open(mock_file, "w", encoding="utf-8") as f:
                json.dump(submissions, f, indent=2)
            log.info("✅ [MOCK] New submission stored locally — Email: %s", payload.email)
        except Exception as e:
            log.error("Mock file write error: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error storing submission.")
    else:
        try:
            # Get current sheet headers or write defaults if empty
            try:
                headers = [h.strip().lower() for h in sheet.row_values(1)]
            except Exception:
                headers = []

            if not headers:
                default_headers = [
                    "Timestamp (UTC)",
                    "First Name",
                    "Last Name",
                    "Full Name",
                    "Email",
                    "Phone",
                    "Company",
                    "Designation",
                    "Service",
                    "Message",
                    "Attachment"
                ]
                sheet.append_row(default_headers, value_input_option="USER_ENTERED")
                headers = [h.strip().lower() for h in default_headers]

            # Construct row based on headers mapping
            row = [None] * len(headers)
            for i, h in enumerate(headers):
                if "timestamp" in h:
                    row[i] = timestamp
                elif "first" in h:
                    row[i] = payload.firstName or ""
                elif "last" in h:
                    row[i] = payload.lastName or ""
                elif "full name" in h or (h == "name" and payload.name):
                    row[i] = payload.name or f"{payload.firstName or ''} {payload.lastName or ''}".strip()
                elif "email" in h:
                    row[i] = payload.email
                elif "phone" in h or "contact" in h:
                    row[i] = payload.phone or ""
                elif "company" in h or "organisation" in h or "organization" in h:
                    row[i] = payload.company or ""
                elif "designation" in h or "title" in h or "role" in h:
                    row[i] = payload.designation or ""
                elif "service" in h:
                    row[i] = payload.service or ""
                elif "message" in h:
                    row[i] = payload.message or ""
                elif "attachment" in h or "file" in h:
                    row[i] = attachment_url or ""

            # Replace any remaining None values with empty string
            row = [x if x is not None else "" for x in row]

            sheet.append_row(row, value_input_option="USER_ENTERED")
            log.info("✅  New submission appended — Email: %s", payload.email)
        except gspread.exceptions.APIError as e:
            log.error("Google Sheets API error: %s", e)
            raise HTTPException(
                status_code=502,
                detail="Could not save your submission. Please try again shortly.",
            ) from e
        except Exception as e:
            log.error("Unexpected error writing to sheet: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error.") from e

    # Trigger SMTP email alert
    send_smtp_alert(payload, attachment_url)

    return {
        "success": True,
        "message": "Thank you! Your message has been received.",
    }
