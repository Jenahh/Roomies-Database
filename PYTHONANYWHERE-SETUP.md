# Publish Roomies with the free PythonAnywhere account

This upload contains the website you tested, its Python API, constrained SQLite
schema and synthetic seed data. No Node.js, pip installation, or local server is
needed on the host. The compiled frontend is included. The 4330 source stays in
its original repository.

## 1. Account and upload

Create/sign in to a **free Beginner** account on www.pythonanywhere.com. Its
username determines the public website address. Use the global US site for
these examples.

In **Files**, upload `Roomies-Public-Hosting.zip` into your home directory.
In **Consoles**, open a **Bash** console and run:

```bash
unzip -o ~/Roomies-Public-Hosting.zip -d ~
cd ~/roomies4402
python3 -m unittest discover -v
python3 roomies.py test
python3 setup_pythonanywhere.py
```

The setup prints a short, personalized WSGI configuration. Keep it for step 2.
It creates `/home/YOURUSERNAME/roomies-data/roomies.sqlite3` only when absent.
Later code uploads replace `roomies4402`, while this separate data directory
keeps saved changes. Do not run initialization over an existing database.

## 2. Create the web app

Open **Web > Add a new web app**. Select the free pythonanywhere.com address,
**Manual configuration**, and an available **Python 3** version (3.10+ is fine).
This project uses the standard library; leave the virtualenv field empty.

Open the **WSGI configuration file** link. Replace the sample contents with the
three lines printed by setup_pythonanywhere.py. For example:

```python
import sys
sys.path.insert(0, '/home/YOURUSERNAME/roomies4402')
from pythonanywhere_wsgi import application
```

Use your actual username in the path, or copy the exact generated lines.
The generated module imports the app without starting an HTTP server. You do
not need to leave a console or computer running.

## 3. Static assets and HTTPS

In the Web tab's **Static files** section, add just this mapping:

| URL | Directory |
| --- | --- |
| `/assets/` | `/home/YOURUSERNAME/roomies4402/web/roomies/assets` |

The Python application serves `/demo/`, API calls and embedded app pages. Do not
map the project root or the data directory to a public static URL.

Enable the **Force HTTPS** option in the Web tab if available, save the WSGI
file, and click **Reload**. Visit:

`https://YOURUSERNAME.pythonanywhere.com/`

The root redirects to the unified Roomies interface. `/health` should return
JSON with `status: ok` and `roomiesAvailable: true`.

## 4. Test the public site

- Open the link in a private browser window and on your phone. The page should
  open without a PythonAnywhere account or ChatGPT login.
- Select Alex: create a chore or shared bill. Select Mia: verify the shared
  record and your expense share.
- Try a monthly bill, record/undo a payment, and check the saved balance.
- Submit maintenance as Alex; update it as Jordan. Submit an RA concern as Mia;
  close it as Taylor. Verify status/history after refreshing.
- Add and delete an empty household as Jordan. Verify it remains deleted after
  refreshing.
- Stop the local preview server and repeat a public-site operation. The public
  website must operate independently of your computer.
- Click Reload in PythonAnywhere and verify your newly saved records remain.

All accounts and data are fictional classroom examples. Account selection is
a public demo shortcut. Use the top account menu to switch people.

## Keeping it available and updating it

Free web apps currently have a one-month expiry. Extend/re-enable the web app
from the account dashboard when required, and keep it available for grading.
Free-plan limits can change; check the provider's current dashboard.

To update application code, upload the next verified hosting ZIP, extract it
over `~/roomies4402`, run setup_pythonanywhere.py again, and Reload. The separate
`~/roomies-data` file is retained. Make a database backup before later updates.
Only the account owner should run resets or replace the persistent data file.

When the public URL is verified, add it and the demo-account instructions to the
README/report. This hosting upload is separate from the final Gradescope code
ZIP, which should also contain the complete report-supporting source assets.

## Official provider references

- https://www.pythonanywhere.com/pricing/
- https://help.pythonanywhere.com/pages/FreeAccountsFeatures/
- https://help.pythonanywhere.com/pages/KindsOfDatabases/
- https://help.pythonanywhere.com/pages/UploadingAndDownloadingFiles/
- https://help.pythonanywhere.com/pages/WebAppBasics/
- https://help.pythonanywhere.com/pages/StaticFiles/
