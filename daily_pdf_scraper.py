import os
import time
import requests
import smtplib
from ftplib import FTP
from bs4 import BeautifulSoup
from datetime import datetime
from email.mime.text import MIMEText

FTP_HOST = os.getenv('FTP_HOST')
FTP_USERNAME = os.getenv('FTP_USERNAME')
FTP_PASSWORD = os.getenv('FTP_PASSWORD')
EMAIL_FROM = os.getenv('EMAIL_FROM')
EMAIL_TO = os.getenv('EMAIL_TO')
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')

LEAGUE_URL = 'https://leaguesecretary.com/bowling-centers/sunshine-lanes/bowling-leagues/wed-mixers-by-missouri-soft-wash/league/standings-png/109647'
PDF_BASE_URL = 'https://www.leaguesecretary.com'
LAST_URL_FILE = 'last_pdf_url.txt'
DOWNLOAD_DIR = 'pdfs'
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
    msg = MIMEText(f"A new PDF is available: https://yourwebsite.com/league_pdfs/{filename}")
    msg['Subject'] = f"New League PDF: {filename}"
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())

if os.path.exists(LAST_URL_FILE):
    with open(LAST_URL_FILE, 'r') as f:
        last_url = f.read().strip()
else:
    last_url = ''

headers = {'User-Agent': 'Mozilla/5.0'}
res = requests.get(LEAGUE_URL, headers=headers)
soup = BeautifulSoup(res.text, 'html.parser')
pdf_tag = soup.find('a', href=lambda x: x and x.endswith('.pdf'))

if pdf_tag:
    href = pdf_tag['href']
    current_url = href if href.startswith('http') else PDF_BASE_URL + href

    if current_url != last_url:
        today = datetime.now().strftime('%Y-%m-%d')
        filename = f'standings_{today}.pdf'
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        pdf_data = download_pdf(current_url)
        with open(filepath, 'wb') as f:
            f.write(pdf_data)
        with open(LAST_URL_FILE, 'w') as f:
            f.write(current_url)
        with FTP(FTP_HOST) as ftp:
            ftp.login(FTP_USERNAME, FTP_PASSWORD)
            ftp.cwd('/public_html/league_pdfs')
            upload_ftp(ftp, filename, filepath)
            upload_ftp(ftp, 'latest.pdf', filepath)
        send_email(filename)
    else:
        print("No new PDF found.")
else:
    print("No PDF link found.")
