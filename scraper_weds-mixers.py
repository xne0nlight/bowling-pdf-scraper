import os
import time
import requests
import smtplib
from ftplib import FTP
from datetime import datetime
from email.mime.text import MIMEText
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

print("Checking for updated PDF...")

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

STANDINGS_URL = 'https://leaguesecretary.com/bowling-centers/sunshine-lanes/bowling-leagues/wed-mixers-by-missouri-soft-wash/league/standings-png/109647'
DOWNLOAD_DIR = 'pdfs'
FTP_SUBDIR = 'league_pdfs/weds-mixers'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def get_latest_pdf_url():
    print("Launching headless browser to extract PDF URL...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get(STANDINGS_URL)

        export_button = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "customExport"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", export_button)
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "customExport"))
        )
        time.sleep(2)
        driver.execute_script("arguments[0].click();", export_button)

        WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > 1)
        driver.switch_to.window(driver.window_handles[1])
        pdf_url = driver.current_url
        print(f"Resolved PDF URL: {pdf_url}")
        return pdf_url

    except Exception as e:
        print(f"Error extracting PDF URL: {e}")
        raise

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
    msg = MIMEText(f"A new Weds. Mixers PDF is available: https://jeffjohnsononline.com/bowling-pdf-scraper/{FTP_SUBDIR}/{filename}")
    msg['Subject'] = "New Weds. Mixers PDF Posted!"
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

# Main logic
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
