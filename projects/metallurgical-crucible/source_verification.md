# Source Verification Notes

Generated from the Gemini source pass and verified manually on 2026-05-15.

## Ready After Download / Upload

| Asset ID | Provider | Verified URL | Rights posture | Use |
| --- | --- | --- | --- | --- |
| MET-IMG-06 | Smithsonian | https://www.si.edu/object/whittle-w1x-turbojet-engine%3Anasm_A19500082000 | CC0 / public domain on object page | Whittle W.1X engine stills |
| MET-IMG-07 | Smithsonian | https://www.si.edu/object/messerschmitt-me-262-1a-schwalbe-swallow%3Anasm_A19600328000 | CC0 / public domain on object page | Me 262 and Jumo nacelle stills |
| MET-VID-04 | DVIDS | https://www.dvidshub.net/video/967617/raising-bar-additive-manufacturing-unbranded | Public domain DVIDS work, VIRIN 250620-A-AP401-1002 | Modern additive manufacturing sequence |
| MET-IMG-05 | NASA | https://www.nasa.gov/?p=412144 | NASA media / U.S. government work, subject to NASA media guidelines | SR-71 afterburner and heat sequence |
| MET-VID-08 | NASA | https://technology.nasa.gov/virtual-event/nasas-additive-manufacturing-alloys-high-temperature-applications-webinar | NASA media / U.S. government work, subject to NASA media guidelines | ODS-MEA / high-temp alloy sequence |
| MET-VID-03 | NARA | https://www.archives.gov/research/guide-fed-records/groups/326.html | Federal records are generally public domain, but specific catalog items must be checked | AEC / atomic metallurgy sequence |

## Rights Review / Do Not Mark Ready Yet

| Asset ID | Provider | Issue |
| --- | --- | --- |
| MET-VID-01 | Yorkshire Film Archive | Likely requires licensing. Useful research lead, not a ready source asset. |
| MET-VID-02 | General Electric | Rights unclear. Use as reference only until GE or archive permissions are explicit. |
| MET-VID-10 | CSIRO / Anatomics | Rights unclear and likely permission-required for broadcast/distribution. |

## Workflow

1. Download or otherwise obtain only rights-safe media from the verified URLs.
2. Upload the files into the Google Drive project folders.
3. Copy rows from `drive_ledger_candidate_rows.csv` into the Drive media ledger.
4. Replace folder placeholders with exact Drive file paths.
5. Change `Status` from `needs_download` or `needs_catalog_pull` to `ready`.
6. Export the ledger tab as CSV and run `python3 -m docuengine ingest-drive-ledger --project-dir projects/metallurgical-crucible --ledger-csv /path/to/media-ledger-export.csv`.

Do not mark NARA RG 326 ready until a specific catalog item or reel has been selected and its use restrictions checked.
