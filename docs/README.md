# Report and evidence

- Roomies-CSC4402-Expanded-Report.pdf: refreshed report with public URL, 18 relations,
  all five E-R panels, five main query results, and current interface illustrations.
- Roomies-CSC4402-Expanded-Report.docx: editable version. Recheck pagination after edits.
- Participation entries still need each teammate's confirmed actual responsibilities.
- er-a through er-d retain the existing model and ISA triangle. er-e-expense-ledger
  adds bill detail, monthly recurrence and payment relationships. The combined
  Roomies-Expanded-ER-Diagrams.pdf contains all five full-size panels.
- query-screenshots/ contains SQL and actual rows for all eleven executable seed
  queries. Queries 1-5 are the main report set; 6-11 are supplementary examples.
- current-web-screenshots/ contains real current-build screenshots from a local
  replay. Maintenance and RA statuses were changed through the API for illustration.
- public-verification.json records public API checks and saved data after a Railway
  restart. These checks are separate from the local screenshot replay.
- The root seed database remains reproducible and separate from all replay/live data.
- Older web-screenshots/, CLI captures and transcripts remain supplementary evidence.

Run python roomies.py test, python -m unittest discover -v, and python verify_demo.py
from the code folder. See the root README for browser and terminal instructions.
