import subprocess

# Run Weds Mixers
subprocess.run(["python", "scraper_weds-mixers.py"], check=True)

# Run Roto Rooters Trios
subprocess.run(["python", "scraper_roto-rooters-trios.py"], check=True)
