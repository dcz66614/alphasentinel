# SEC fixtures

These files are cuts of SEC companyfacts JSON. Fact objects that remain
were copied from the downloaded response. Amounts were not typed by hand.

Downloaded: 2026-10-27

What was kept:

- `cik` and `entityName`
- us-gaap concepts the normalizer reads, including each concept's SEC
  `label` and `description` when the response had them
- `USD` and `shares` units only
- 10-K and 10-K/A facts whose `end` is the single period named below,
  including shorter facts that share that end date

## AAPL

- CIK: 0000320193
- Source URL: https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json
- Period end kept: 2025-09-27
- File: `aapl_companyfacts_excerpt.json`

## MSFT

- CIK: 0000789019
- Source URL: https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json
- Period end kept: 2026-06-30
- File: `msft_companyfacts_excerpt.json`

## AAPL Form 4

Whole ownership XML response, copied from the download. Amounts were not typed by hand.

Downloaded: 2026-10-27

- Accession: 0000320193-23-000088
- Filing date: 2023-10-03
- Submissions `primaryDocument`: `xslF345X05/wk-form4_1696381345.xml`
- Ownership XML URL: https://www.sec.gov/Archives/edgar/data/320193/000032019323000088/wk-form4_1696381345.xml
- File: `aapl_form4_0000320193-23-000088.xml`

## Offline cache

`offline_cache/` is what `tests/test_forensic.py` reads instead of `data/cache/`.
Files were cut from the local download dated 2026-10-27. Amounts, closes, and
filing text were copied. They were not typed by hand.

`companyfacts.json` keeps `cik`, `entityName`, and the us-gaap concepts the
normalizer reads (`label` and `description` included when the response had
them). Units are `USD` and `shares` only. Facts kept are 10-K and 10-K/A rows
whose `end` is one of the period ends below, including shorter facts that share
that end. AAPL keeps three ends so the Piotroski check can see a lagged year.
The ingest path keeps two years, so `index.json` lists those two only.

`index.json` keeps ticker, CIK, source URLs, and the matching year records from
the cached index. Each year lists the one Form 4 file copied below.

Submissions snippets keep `cik`, `entityType`, `sic`, `sicDescription`, `name`,
`tickers`, and `exchanges` from the company submissions file. The `filings`
object was left out.

Each 10-K file is the first 80,000 characters of the cached HTML, decoded as
UTF-8 and written back as UTF-8. Each Form 4 file is the whole cached XML.

`prices.csv` is an unedited slice of the cached yfinance file: the header plus
rows whose session is on the period end or within the prior 14 days.
`prices_source` on the index is `yfinance.Ticker.history auto_adjust=false`.

### AAPL

- CIK: 0000320193
- Companyfacts URL: https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json
- Companyfacts ends kept: 2023-09-30, 2024-09-28, 2025-09-27
- File: `offline_cache/AAPL/companyfacts.json`
- Submissions URL: https://data.sec.gov/submissions/CIK0000320193.json
- File: `offline_cache/AAPL/submissions/CIK0000320193.json`
- SIC copied from that file: 3571, Electronic Computers

10-K prefixes:

- FY2024 accession 0000320193-24-000123, 1,503,901 characters in the download, 80,000 kept
- URL: https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm
- File: `offline_cache/AAPL/filings/0000320193-24-000123/aapl-20240928.htm`
- FY2025 accession 0000320193-25-000079, 1,520,329 characters in the download, 80,000 kept
- URL: https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm
- File: `offline_cache/AAPL/filings/0000320193-25-000079/aapl-20250927.htm`

Form 4 files, copied whole. Each is the smallest cached ownership file for that
year that has an open-market code P or S inside the fiscal period:

- FY2024 accession 0000320193-23-000113
- Primary document: `xslF345X05/wk-form4_1701473530.xml`
- URL: https://www.sec.gov/Archives/edgar/data/320193/000032019323000113/wk-form4_1701473530.xml
- File: `offline_cache/AAPL/ownership/0000320193-23-000113.xml`
- FY2025 accession 0000320193-24-000129
- Primary document: `xslF345X05/wk-form4_1732059042.xml`
- URL: https://www.sec.gov/Archives/edgar/data/320193/000032019324000129/wk-form4_1732059042.xml
- File: `offline_cache/AAPL/ownership/0000320193-24-000129.xml`

Price rows kept are cached sessions on the period end or within the prior 14 days:
2024-09-16 to 2024-09-27, and 2025-09-15 to 2025-09-26.
File: `offline_cache/AAPL/prices.csv`

### MSFT

- CIK: 0000789019
- Companyfacts URL: https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json
- Companyfacts ends kept: 2025-06-30, 2026-06-30
- File: `offline_cache/MSFT/companyfacts.json`
- Submissions URL: https://data.sec.gov/submissions/CIK0000789019.json
- File: `offline_cache/MSFT/submissions/CIK0000789019.json`
- SIC copied from that file: 7372, Services-Prepackaged Software

10-K prefixes:

- FY2025 accession 0000950170-25-100235, 8,158,188 characters in the download, 80,000 kept
- URL: https://www.sec.gov/Archives/edgar/data/789019/000095017025100235/msft-20250630.htm
- File: `offline_cache/MSFT/filings/0000950170-25-100235/msft-20250630.htm`
- FY2026 accession 0001193125-26-323660, 8,585,622 characters in the download, 80,000 kept
- URL: https://www.sec.gov/Archives/edgar/data/789019/000119312526323660/msft-20260630.htm
- File: `offline_cache/MSFT/filings/0001193125-26-323660/msft-20260630.htm`

Form 4 files, copied whole, chosen the same way as AAPL:

- FY2025 accession 0001062993-24-019650
- Primary document: `xslF345X05/form4.xml`
- URL: https://www.sec.gov/Archives/edgar/data/789019/000106299324019650/form4.xml
- File: `offline_cache/MSFT/ownership/0001062993-24-019650.xml`
- FY2026 accession 0000789019-26-000048
- Primary document: `xslF345X05/form4.xml`
- URL: https://www.sec.gov/Archives/edgar/data/789019/000078901926000048/form4.xml
- File: `offline_cache/MSFT/ownership/0000789019-26-000048.xml`

Price rows kept are cached sessions on the period end or within the prior 14 days:
2025-06-16 to 2025-06-30, and 2026-06-16 to 2026-06-30.
File: `offline_cache/MSFT/prices.csv`
