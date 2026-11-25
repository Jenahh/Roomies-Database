# Start here — Roomies CSC 4402

Public demo: https://roomies-web-production.up.railway.app/

For the submission ZIP, extract it and open the `roomies4402` folder in VS Code.
Run `python web_preview.py`, then open http://127.0.0.1:8080/demo/ . The compiled
interface is included; no separate frontend install is required.

Run the checks:

```powershell
python roomies.py test
python -m unittest discover -v
python verify_demo.py
```

The supplied seed is preserved. Local browser edits go to
`demo-local-honors.sqlite3`; hosted edits go to the separate persistent Railway
volume. Demo account selection is for fictional classroom identities.

Read README.md for accounts, terminal menus, query results, rebuilding, and hosting.
The report and full-size E-R figures are in docs/. Confirm team participation
entries and the report's final page count before submission.
