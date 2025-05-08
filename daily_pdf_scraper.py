import os
import time
import requests
import smtplib
from ftplib import FTP
from datetime import datetime
from email.mime.text import MIMEText

# Environment variables
FTP_HOST = os.getenv('FTP_HOST')
FTP_USERNAME = os.getenv('FTP_USERNAME')
FTP_PASSWORD = os.getenv('FTP_PASSWORD')
EMAIL_FROM = os.getenv('EMAIL_FROM')
EMAIL_TO = os.getenv('EMAIL_TO')
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')

# Constants
PDF_URL = 'https://www.leaguesecretary.com/uploads/2024/f/33/10964704302025f202433standg00.pdf'
DOWNLOAD_DIR = 'pdfs'
LAST_URL_FILE = 'last_pdf_url.txt'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def download_pdf(url, retries=3, delay=5):
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.content
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
        time.sleep(delay)
    raise Exception("Download failed after multiple attempts.")

def upload_ftp(ftp, filename, filepath, retries=3, delay=5):
    for attempt in range(retries):
        try:
            with open(filepath, 'rb') as f:
                ftp.storbinary(f'STOR {filename}', f)
            return
        except Exception as e:
            print(f"FTP attempt {attempt+1} failed: {e}")
            time.sleep(delay)
    raise Exception("FTP upload failed after multiple attempts.")

def send_email(filename):
    msg = MIMEText(f"A new PDF is available: https://jeffjohnsononline.com/league_pdfs/{filename}")
    msg['Subject'] = f"New League PDF: {filename}"
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())

def ensure_directory(ftp, path):
    try:
        ftp.cwd(path)
    except Exception:
        ftp.mkd(path)
        ftp.cwd(path)

# Check if already downloaded
if os.path.exists(LAST_URL_FILE):
    with open(LAST_URL_FILE, 'r') as f:
        last_url = f.read().strip()
else:
    last_url = ''

if PDF_URL != last_url:
    today = datetime.now().strftime('%Y-%m-%d')
    filename = f'standings_{today}.pdf'
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    pdf_data = download_pdf(PDF_URL)
    with open(filepath, 'wb') as f:
        f.write(pdf_data)
    with open(LAST_URL_FILE, 'w') as f:
        f.write(PDF_URL)

    with FTP(FTP_HOST) as ftp:
        ftp.login(FTP_USERNAME, FTP_PASSWORD)
        ensure_directory(ftp, 'league_pdfs')
        upload_ftp(ftp, filename, filepath)
        upload_ftp(ftp, 'latest.pdf', filepath)

    send_email(filename)
else:
    print("No new PDF detected; skipping.")
