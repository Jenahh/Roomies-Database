# Publish the Roomies CSC4402 classroom demo on Railway

The current Free plan has no subscription or credit card requirement. It grants
$1 of resource usage per month, including compute, storage and outbound traffic.
Services sleep when idle. Exhausting the credit pauses the site until the next
cycle; this is not a guarantee of uninterrupted hosting. New accounts start with
a separate $5/30-day trial. At its end, select Free on the Plans page and redeploy;
do not select Hobby or add a payment method if the project must remain free.

Official references (checked November 24, 2026):
- https://docs.railway.com/pricing/free-plan
- https://docs.railway.com/volumes
- https://docs.railway.com/builds/dockerfiles
- https://docs.railway.com/deployments/healthchecks

## What gets deployed

One service serves the interface and Python API at the same origin. Its
SQLite file is stored on one attached volume. No additional Postgres/MySQL
service is needed. The Docker build fetches Roomies revision
`a294a7e4b2903a76be7d9a4319bf6a57825a8eae`, runs its locked npm install,
and applies the existing CSC4402 build adapter in memory. Only compiled browser
assets enter the final Python image. The original Roomies repository is not
edited, and its React source is not added to this repository.

The ordinary local preview and CLI still require only Python's standard library.
The hosted image adds the pinned Gunicorn WSGI server.

## Deploy after these files are available on the database repository branch

1. In Railway, choose **New Project > Deploy from GitHub repo**. Select
   **Jenahh/Roomies-Database** and the branch containing this Dockerfile and the
   complete preview changes. Do not select the separate Roomies app repository.
   Railway detects the Dockerfile automatically. You need repository access
   through GitHub; an owner may need to authorize the repository for Railway.
2. Attach a **volume to this service**, with mount path **`/data`**. The Free
   plan's volume limit is 0.5 GB. The first attempt can fail until this is attached;
   startup deliberately rejects a Railway deployment without persistent storage.
3. The Docker image already sets these variables. Keep them at these values:

   | Variable | Value |
   | --- | --- |
   | ROOMIES_DB_PATH | /data/roomies.sqlite3 |
   | ROOMIES_FRONTEND_DIR | /app/web/roomies |

   Railway supplies `PORT` and `RAILWAY_VOLUME_MOUNT_PATH`. The server listens
   on `0.0.0.0:$PORT`. Do not point the database at the code folder or seed file.
4. In service settings, set **Healthcheck Path** to **`/health`**, keep **one
   replica**, and enable **Serverless** if that setting is offered during the
   trial. Do not add an external keep-alive/uptime ping that prevents sleeping.
5. Deploy. Once healthy, use **Settings > Networking > Public Networking >
   Generate Domain**. Open the resulting HTTPS address; `/` opens the unified
   Roomies demo. The startup seed runs only when the working database is absent;
   ordinary restarts and deployments reuse saved data.

No `railway.json` or `railway.toml` is required. Settings are configured on the
service rather than using Railway's deprecated Config as Code format.

## Check the public result before sharing it for grading

- Open the HTTPS link on your phone using cellular data and on a private browser.
  Your laptop's local Python server should be stopped.
- Confirm `/health` returns `status: ok` and `roomiesAvailable: true`.
- Add a chore as Alex. Refresh and confirm it remains.
- Submit maintenance as Alex; change its status as Jordan. Refresh as Alex and
  check the updated status; verify the history under Details.
- Test the RA concern workflow using Mia and Taylor.
- Add a bill, record/undo a payment, and test the monthly rule in Bills.
- As Jordan, create and delete an empty household through Details.
- Redeploy/restart the same service without removing its volume. Confirm a
  saved test chore or bill survives. Deleting the service's volume deletes its
  saved database; make a backup before changing storage.
- Confirm `/roomies-database.sqlite3` and `/schema.sql` return 404.
- Check usage and account plan before the instructor's grading window. A public
  URL alone does not establish compliance with any additional Honors criteria;
  include the tested URL and hosting limitations in the final report/README.

All identities and data in this application are fictional classroom examples.
The account selector is demo identity selection, not secure password login.

## Optional local container check (Docker Desktop must be running)

```powershell
docker build -t roomies4402 .
docker volume create roomies4402-data
docker run --rm -p 8080:8080 --mount source=roomies4402-data,target=/data roomies4402
```

Open http://localhost:8080/ . Stop and rerun the same `docker run` command to
check persistence. This local container check does not publish the project.

## If the deployment fails

- **Attach a persistent Railway volume**: attach the volume at `/data`, then
  redeploy. Do not bypass the check by manually setting Railway's mount variable.
- **GitHub checkout fails in the frontend stage**: confirm the pinned app
  revision remains publicly readable. Review a new revision before changing the
  Docker build argument; a newer app may require adapter changes.
- **Adapter interface changed**: build_database_frontend.mjs intentionally stops
  if the source hook call no longer matches. Review the adapter instead of
  publishing an unconnected expense UI.
- **Credit exhausted**: remain on Free and wait for its next reset, or agree on
  an alternative with the instructor. Do not add paid resources to fix this
  without the team's agreement.
