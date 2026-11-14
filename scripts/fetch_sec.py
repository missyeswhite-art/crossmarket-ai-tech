
import json
import os
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

COMPANIES = {
    "NVIDIA": 1045810,
    "AMD": 2488,
    "Broadcom": 1730168,
}
FORMS = {"8-K", "10-K", "10-Q", "8-K/A", "10-K/A", "10-Q/A"}
OUT = Path("data/filings.json")

contact = os.environ.get("SEC_CONTACT_EMAIL", "").strip()
if not contact or "@" not in contact:
    raise RuntimeError("Configure SEC_CONTACT_EMAIL in GitHub Actions secrets")

filings = []
errors = []

for company, cik in COMPANIES.items():
    url = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"CrossMarketAI research {contact}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.load(response)

        recent = data["filings"]["recent"]
        for i, form in enumerate(recent["form"]):
            if form not in FORMS:
                continue

            accession = recent["accessionNumber"][i]
            document = recent["primaryDocument"][i]
            accession_path = accession.replace("-", "")
            filing_url = (
                f"https://www.sec.gov/Archives/edgar/data/"
                f"{cik}/{accession_path}/{document}"
            )

            filings.append({
                "id": accession,
                "company": company,
                "form": form,
                "date": recent["filingDate"][i],
                "description": recent["primaryDocument"][i],
                "url": filing_url,
                "source": "SEC EDGAR",
                "status": "官方申报记录，正文尚未分析",
            })

    except Exception as exc:
        errors.append(f"{company}: {exc}")

    time.sleep(0.5)

if not filings:
    raise RuntimeError("No SEC filings retrieved: " + "; ".join(errors))

filings.sort(key=lambda x: x["date"], reverse=True)

payload = {
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "source": "SEC EDGAR submissions API",
    "filings": filings[:150],
    "errors": errors,
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print(f"Saved {len(payload['filings'])} filings")
if errors:
    print("Partial errors:", errors)
