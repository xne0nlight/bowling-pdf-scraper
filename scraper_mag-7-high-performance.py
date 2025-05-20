import os
import time
import requests
import smtplib
from bs4 import BeautifulSoup
from ftplib import FTP
from datetime import datetime
from email.mime.text import MIMEText
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from webdriver_manager.chrome import ChromeDriverManager

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

LEAGUE_PAGE_URL = "https://leaguesecretary.com/bowling-centers/enterprise-park-lanes/bowling-leagues/mag-7-high-performance/league/standings-png/132098"
DOWNLOAD_DIR = 'pdfs'
FTP_SUBDIR = 'league_pdfs/mag-7-high-performance'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def get_latest_pdf_url():
    print("Launching headless browser to extract PDF URL...")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get(LEAGUE_PAGE_URL)
        WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "customExport"))
        ).click()
        time.sleep(5)

        logs = driver.get_log("performance")
        for entry in logs:
            message = entry["message"]
            if "Network.responseReceived" in message and ".pdf" in message:
                url_start = message.find("https://")
                url_end = message.find(".pdf") + 4
                if url_start != -1 and url_end != -1:
                    pdf_url = message[url_start:url_end]
                    print(f"Resolved PDF URL: {pdf_url}")
                    return pdf_url

        raise Exception("PDF redirect not found in browser logs.")
    finally:
        driver.quit()

def download_pdf(url):
    print(f"Downloading PDF from: {url}")
    response = requests.get(url, timeout=15)
    if response.status_code == 200:
        return response.content
    raise Exception("Failed to download PDF.")

def download_latest_from_ftp():
    print("Connecting to FTP to retrieve latest.pdf for comparison...")
    try:
        with FTP(FTP_HOST) as ftp:
            ftp.login(FTP_USERNAME, FTP_PASSWORD)
            ftp.cwd(FTP_SUBDIR)
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

# Start process
pdf_url = get_latest_pdf_url()
pdf_data = download_pdf(pdf_url)

# Compare to FTP
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

# Upload & email
with FTP(FTP_HOST) as ftp:
    ftp.login(FTP_USERNAME, FTP_PASSWORD)
    ensure_directory(ftp, FTP_SUBDIR)
    upload_ftp(ftp, filename, filepath)
    upload_ftp(ftp, 'latest.pdf', filepath)

send_email(filename)
