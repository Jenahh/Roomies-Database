# Public deployment

- Public address: https://roomies-web-production.up.railway.app/
- Source: Jenahh/Roomies-Database, honors-public-demo, commit 05153a128799abe473140efd56d928aa37bb7349.
- Railway project: roomies-4402 (0d6b0fd5-ce60-4e07-9c0a-f2e4c0186f35).
- Environment: production (4b05d7e3-ad57-4549-a034-8d9971d0c650).
- Service: roomies-web (2845cb94-7d35-49ee-b578-577c86b5b223), one replica, idle sleep enabled.
- SQLite: /data/roomies.sqlite3 on the attached roomies-sqlite volume.
- Public API and restart checks: docs/public-verification.json.
- Existing app source remains fixed at a294a7e4b2903a76be7d9a4319bf6a57825a8eae.

The website works independently of the developer's laptop. Free-plan credit limits
and post-trial plan selection still apply; see RAILWAY-SETUP.md. The dataset in the
submission ZIP is the reproducible seed, not a snapshot of visitors' live edits.
