import os
import time
import requests
import smtplib
from ftplib import FTP
from datetime import datetime
from email.mime.text import MIMEText
from bs4 import BeautifulSoup

print("Checking for updated PDF...")

FTP_HOST = os.getenv('FTP_HOST')
FTP_USERNAME = os.getenv('FTP_USERNAME')
FTP_PASSWORD = os.getenv('FTP_PASSWORD')
EMAIL_FROM = os.getenv('EMAIL_FROM')
EMAIL_TO = os.getenv('EMAIL_TO')
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')

STANDINGS_PAGE_URL = 'https://leaguesecretary.com/bowling-centers/sunshine-lanes/bowling-leagues/rotorooter-trios-by-tml-casework/league/standings-png/139197'
DOWNLOAD_DIR = 'pdfs'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def extract_pdf_url():
    try:
        print("Fetching standings page HTML...")
        response = requests.get(STANDINGS_PAGE_URL, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        # Look for anchor tag that links directly to PDF
        pdf_link = soup.find('a', href=lambda href: href and href.endswith('.pdf'))
        if not pdf_link:
            raise Exception("PDF <a> link not found in page.")
        full_url = "https://www.leaguesecretary.com" + pdf_link['href']
        print(f"Resolved PDF URL: {full_url}")
        return full_url
    except Exception as e:
        print(f"Error extracting PDF URL: {e}")
        raise





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
            ftp.cwd('league_pdfs/roto-rooters-trios')
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
    msg = MIMEText(f"A new Roto-Rooters Trios PDF is available: https://jeffjohnsononline.com/bowling-pdf-scraper/league_pdfs/roto-rooters-trios/{filename}")
    msg['Subject'] = f"New Roto-Rooters Trios PDF Posted!"
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

# Fetch and download latest PDF
pdf_url = extract_pdf_url()
pdf_data = download_pdf(pdf_url)

# Compare with FTP-stored latest.pdf
ftp_latest_data = download_latest_from_ftp()
if ftp_latest_data and ftp_latest_data == pdf_data:
    print("PDF content matches latest.pdf on FTP. Skipping update.")
    exit(0)

# Save locally
today = datetime.now().strftime('%Y-%m-%d')
filename = f'standings_{today}.pdf'
filepath = os.path.join(DOWNLOAD_DIR, filename)
with open(filepath, 'wb') as f:
    f.write(pdf_data)
print(f"PDF saved as {filename}")

# Upload to FTP
with FTP(FTP_HOST) as ftp:
    ftp.login(FTP_USERNAME, FTP_PASSWORD)
    ensure_directory(ftp, 'league_pdfs/roto-rooters-trios')
    upload_ftp(ftp, filename, filepath)
    upload_ftp(ftp, 'latest.pdf', filepath)

# Notify
send_email(filename)
