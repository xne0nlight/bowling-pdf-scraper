
import os
import time
import requests
import smtplib
from ftplib import FTP
from datetime import datetime
from email.mime.text import MIMEText
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

print("Checking for updated PDF...")

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

STANDINGS_URL = 'https://leaguesecretary.com/bowling-centers/enterprise-park-lanes/bowling-leagues/mag-7-high-performance/league/standings-png/132098'
FTP_SUBDIR = 'league_pdfs/mag-7-high-performance'
DOWNLOAD_DIR = 'pdfs'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def get_latest_pdf_url():
    print("Launching headless browser to extract PDF URL...")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    with webdriver.Chrome(executable_path=ChromeDriverManager().install(), options=options) as driver:
        driver.get(STANDINGS_URL)
        time.sleep(5)  # Allow time for JavaScript to load
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        button = soup.find('button', id='customExport')
        if not button or 'onclick' not in button.attrs:
            raise Exception("PDF button not found or missing expected attributes.")
        onclick_value = button['onclick']
        start = onclick_value.find("'") + 1
        end = onclick_value.find("'", start)
        pdf_path = onclick_value[start:end]
        if not pdf_path.startswith("http"):
            pdf_url = "https://www.leaguesecretary.com" + pdf_path
        else:
            pdf_url = pdf_path
        print(f"Resolved PDF URL: {pdf_url}")
        return pdf_url

def download_pdf(url):
    print(f"Downloading PDF from: {url}")
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                return response.content
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
        time.sleep(5)
    raise Exception("Failed to download PDF after multiple attempts.")

def download_latest_from_ftp():
    print("Connecting to FTP to retrieve latest.pdf for comparison...")
    try:
        with FTP(FTP_HOST) as ftp:
            ftp.login(FTP_USERNAME, FTP_PASSWORD)
            ftp.cwd(FTP_SUBDIR)
            local_path = os.path.join(DOWNLOAD_DIR, "latest_from_ftp.pdf")
            with open(local_path, 'wb') as f:
                ftp.retrbinary('RETR latest.pdf', f.write)
            with open(local_path, 'rb') as f:
                print("Downloaded latest.pdf from FTP for comparison.")
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
    msg = MIMEText(f"A new MAG7 High Performance PDF is available: https://jeffjohnsononline.com/{FTP_SUBDIR}/{filename}")
    msg['Subject'] = "New MAG7 High Performance PDF Posted!"
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

pdf_url = get_latest_pdf_url()
pdf_data = download_pdf(pdf_url)
ftp_latest_data = download_latest_from_ftp()
if ftp_latest_data and ftp_latest_data == pdf_data:
    print("PDF content matches latest.pdf on FTP. Skipping update.")
    exit(0)

today = datetime.now().strftime('%Y-%m-%d')
filename = f'standings_{today}.pdf'
filepath = os.path.join(DOWNLOAD_DIR, filename)
with open(filepath, 'wb') as f:
    f.write(pdf_data)
print(f"PDF saved as {filename}")

with FTP(FTP_HOST) as ftp:
    ftp.login(FTP_USERNAME, FTP_PASSWORD)
    ensure_directory(ftp, FTP_SUBDIR)
    upload_ftp(ftp, filename, filepath)
    upload_ftp(ftp, 'latest.pdf', filepath)

send_email(filename)
