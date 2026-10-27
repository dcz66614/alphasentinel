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
