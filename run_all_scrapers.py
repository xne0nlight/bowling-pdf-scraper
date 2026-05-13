import subprocess
import sys

# ============================================================
# Run All Bowling League Scrapers
# ============================================================
# Each scraper runs independently — if one fails, the others
# still get their shot. A summary prints at the end showing
# which ones passed and which ones struck out. (pun intended)
# ============================================================

scrapers = [
    "scraper_weds-mixers.py",
    "scraper_roto-rooters-trios.py",
    "scraper_mag-7-high-performance.py",
]

results = {}

for scraper in scrapers:
    print(f"\n{'='*60}")
    print(f"  Running: {scraper}")
    print(f"{'='*60}\n")
    try:
        subprocess.run([sys.executable, scraper], check=True)
        results[scraper] = "✓ Success"
    except subprocess.CalledProcessError as e:
        results[scraper] = f"✗ Failed (exit code {e.returncode})"
    except Exception as e:
        results[scraper] = f"✗ Error: {e}"

# Print summary
print(f"\n{'='*60}")
print("  SCRAPER SUMMARY")
print(f"{'='*60}")
for scraper, status in results.items():
    print(f"  {status}  —  {scraper}")
print(f"{'='*60}\n")

# Exit with error code if ANY scraper failed
# (so GitHub Actions marks the run as failed and you can see it)
failed = any("✗" in status for status in results.values())
if failed:
    print("One or more scrapers failed. Check logs above for details.")
    sys.exit(1)
else:
    print("All scrapers completed successfully. Strike!")
    sys.exit(0)
