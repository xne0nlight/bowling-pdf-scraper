import os
import time
import smtplib
import requests
from ftplib import FTP
from datetime import datetime
from email.mime.text import MIMEText
from bs4 import BeautifulSoup

print("Checking for updated Weds Mixers PDF...")

# Load environment variables
FTP_HOST = os.getenv('FTP_HOST')
FTP_USERNAME = os.getenv('FTP_USERNAME')
FTP_PASSWORD = os.getenv('FTP_PASSWORD')
EMAIL_FROM = os.getenv('EMAIL_FROM')
EMAIL_TO = os.getenv('EMAIL_TO')
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')

DOWNLOAD_DIR = 'pdfs'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

LEAGUE_PAGE_URL = "https://leaguesecretary.com/bowling-centers/sunshine-lanes/bowling-leagues/wed-mixers-by-missouri-soft-wash/league/standings-png/109647"

def find_pdf_url_from_league_page():
    print("Fetching league page...")
    res = requests.get(LEAGUE_PAGE_URL)
    soup = BeautifulSoup(res.text, 'html.parser')
    for script in soup.find_all("script"):
        if ".pdf" in script.text and "uploads/" in script.text:
            start = script.text.find("uploads/")
            end = script.text.find(".pdf", start) + 4
            return "https://www.leaguesecretary.com/" + script.text[start:end]
    raise Exception("PDF URL not found in page.")

def download_pdf(url, retries=3, delay=5):
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print(f"Downloaded PDF from attempt {attempt+1}")
                return response.content
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
        time.sleep(delay)
    raise Exception("Download failed after multiple attempts.")

def download_latest_from_ftp():
    print("Connecting to FTP to retrieve latest.pdf for comparison...")
    try:
        with FTP(FTP_HOST) as ftp:
            ftp.login(FTP_USERNAME, FTP_PASSWORD)
            ftp.cwd('league_pdfs/weds-mixers')
            local_path = os.path.join(DOWNLOAD_DIR, "latest_from_ftp.pdf")
            with open(local_path, 'wb') as f:
                ftp.retrbinary('RETR latest.pdf', f.write)
            print("Downloaded latest.pdf from FTP for comparison.")
            with open(local_path, 'rb') as f:
                return f.read()
    except Exception as e:
        print(f"Could not retrieve latest.pdf from FTP: {e}")
        return None

def upload_ftp(ftp, filename, filepath, retries=3, delay=5):
    for attempt in range(retries):
        try:
            with open(filepath, 'rb') as f:
                ftp.storbinary(f'STOR {filename}', f)
            print(f"Uploaded: {filename}")
            return
        except Exception as e:
            print(f"FTP attempt {attempt+1} failed: {e}")
            time.sleep(delay)
    raise Exception("FTP upload failed after multiple attempts.")

def send_email(filename):
    msg = MIMEText(f"A new Weds. Mixers PDF is available: https://jeffjohnsononline.com/bowling-pdf-scraper/league_pdfs/weds-mixers/{filename}")
    msg['Subject'] = f"New Weds. Mixers PDF Posted!"
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())
    print("Notification email sent.")

def ensure_directory(ftp, path):
    try:
        ftp.cwd(path)
    except Exception:
        ftp.mkd(path)
        ftp.cwd(path)

# Start scraping
PDF_URL = find_pdf_url_from_league_page()
pdf_data = download_pdf(PDF_URL)

ftp_latest_data = download_latest_from_ftp()
if ftp_latest_data and ftp_latest_data == pdf_data:
    print("PDF content matches latest.pdf on FTP. Skipping update.")
    exit(0)

# Save new version locally
today = datetime.now().strftime('%Y-%m-%d')
filename = f'standings_{today}.pdf'
filepath = os.path.join(DOWNLOAD_DIR, filename)
with open(filepath, 'wb') as f:
    f.write(pdf_data)
print(f"PDF saved as {filename}")

# Upload to FTP and notify
with FTP(FTP_HOST) as ftp:
    ftp.login(FTP_USERNAME, FTP_PASSWORD)
    ensure_directory(ftp, 'league_pdfs/weds-mixers')
    upload_ftp(ftp, filename, filepath)
    upload_ftp(ftp, 'latest.pdf', filepath)

send_email(filename)
