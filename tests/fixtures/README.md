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

## Tag-gap excerpts

Same cut rules as the AAPL and MSFT excerpts above: `cik`, `entityName`, and the
us-gaap concepts named below. `label` and `description` were copied when the
response had them. Units are `USD` and `shares` only. Facts kept are 10-K and
10-K/A rows. Amounts were not typed by hand.

Downloaded: 2026-10-28, except META, which was cut from the companyfacts file
already in `data/cache/META/` from the A09 pipeline download of the same URL.

Where a concept is absent from the excerpt, it was absent from that response
for the kept periods. Nothing was added to fill the gap.

### META

- CIK: 0001326801
- Source URL: https://data.sec.gov/api/xbrl/companyfacts/CIK0001326801.json
- Period ends kept: 2024-12-31, 2025-12-31
- File: `meta_companyfacts_excerpt.json`
- `CommonStockSharesOutstanding` is not in the response. The `dei` namespace
  in that response has `EntityPublicFloat` and does not have
  `EntityCommonStockSharesOutstanding`. The excerpt keeps the fy 2024 and
  fy 2025 10-K `EntityPublicFloat` facts. Those ends are 2024-06-30 and
  2025-06-30. They are not period-end shares.
- The excerpt keeps `WeightedAverageNumberOfSharesOutstandingBasic` and
  `WeightedAverageNumberOfDilutedSharesOutstanding` for the balance-sheet
  ends. Those are duration facts used for earnings per share.
  `shares_outstanding` stays NULL. The weighted average is not used.

### AMZN

- CIK: 0001018724
- Source URL: https://data.sec.gov/api/xbrl/companyfacts/CIK0001018724.json
- Period ends kept: 2024-12-31, 2025-12-31
- File: `amzn_companyfacts_excerpt.json`
- Selling and marketing is `MarketingExpense`. The response has no
  `SellingAndMarketingExpense` and no `SellingGeneralAndAdministrativeExpense`.
- The response has no `ResearchAndDevelopmentExpense`. No concept name or
  label in the response contains Technology, Fulfillment, or infrastructure.
  `rd_expense` stays NULL.
- `Liabilities` is absent. `LiabilitiesNoncurrent` 10-K facts in the response
  end in 2011, so those older facts are kept as well. They are not 2024 or 2025
  balances.
- `StockholdersEquity` and `LiabilitiesAndStockholdersEquity` are kept for
  the two period ends. `LiabilitiesAndStockholdersEquity` equals `Assets` on
  each own-year fact. The response has no
  `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest`
  and no `MinorityInterest` balance. `total_liabilities` is derived as
  `Assets` minus `StockholdersEquity` for that same period on the year's own
  10-K, and the record marks the field derived.
- `dei:EntityCommonStockSharesOutstanding` 10-K facts for fy 2024 and fy 2025
  are kept. Their ends are 2025-01-29 and 2026-01-28, the cover dates, not
  2024-12-31 or 2025-12-31. They are not used as `shares_outstanding`. The
  period-end count remains `CommonStockSharesOutstanding`.

### ORCL

- CIK: 0001341439
- Source URL: https://data.sec.gov/api/xbrl/companyfacts/CIK0001341439.json
- Period ends kept: 2025-05-31, 2026-05-31
- File: `orcl_companyfacts_excerpt.json`
- Noncurrent notes are `LongTermNotesPayable`. The response has no
  `LongTermDebtNoncurrent` on these ends.
- `LongTermDebt` has one 10-K fact in the response, end 2022-05-31, value 0.
  That fact is kept. `CostOfRevenue` 10-K facts stop in 2011 and are kept.
  Neither is a 2025 or 2026 amount. The response has no
  `CostOfGoodsAndServicesSold`. `cogs` stays NULL.
- `CostsAndExpenses` for the two period ends is kept. Its label is the total
  of costs and expenses. It is not used as cost of revenue, and it is not
  subtracted down to a cost-of-revenue figure.

### GOOGL

- CIK: 0001652044
- Source URL: https://data.sec.gov/api/xbrl/companyfacts/CIK0001652044.json
- Period ends kept: 2024-12-31, 2025-12-31
- File: `googl_companyfacts_excerpt.json`
- `Revenues` for 2024-12-31 is the comparative column in the 10-K filed
  2026-02-05, accession 0001652044-26-000018, `fy` 2025.
- `RevenueFromContractWithCustomerExcludingAssessedTax` for 2024-12-31 is the
  2024 10-K, accession 0001652044-25-000014, `fy` 2024. Same revenue amount.
  The normalizer keeps that filing.

### PLTR

- CIK: 0001321655
- Source URL: https://data.sec.gov/api/xbrl/companyfacts/CIK0001321655.json
- Period ends kept: 2024-12-31, 2025-12-31
- File: `pltr_companyfacts_excerpt.json`
- `LongTermDebtNoncurrent` 10-K facts in the response stop at 2021-12-31,
  including a zero. Those facts are kept. The 2024 and 2025 10-Ks do not
  repeat the tag, and they do not contain another long-term debt fact of
  zero. That 2021 zero is not carried forward. `long_term_debt` stays NULL.
- `OperatingLeaseLiabilityNoncurrent` for the two kept ends is a lease
  liability, not that debt line. It is not used as `long_term_debt`.
