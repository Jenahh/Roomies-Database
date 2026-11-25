# Integration sources and verified deployment

- Database source: Jenahh/Roomies-Database, expanded schema work at b73fa25;
  this integration started from dev c30e69a.
- Public integration branch: honors-public-demo in Jenahh/Roomies-Database.
- Verified public deployment commit: 05153a128799abe473140efd56d928aa37bb7349.
- Fixed frontend source: Jenahh/Roomies a294a7e4b2903a76be7d9a4319bf6a57825a8eae.
- Original chore/request API contract: Jenahh/Roomies a08383b.

The Dockerfile fetches the fixed frontend revision in a disposable build stage.
The adapter replaces the ledger hook and its identity argument in memory. Only
compiled browser assets enter the final Python image. The app checkout, its
normal dist folder, and the separate 4330 repository are unchanged.

The CSC4402 wrapper provides shared demo identity, direct primary navigation,
and additional database tools. Browser and CLI operations share role/household
checks and relational constraints. ExpenseDetail, ExpenseRecurrence and
ExpensePayment bring the schema to 18 tables, including optional ChoreDisplay.
Older working databases receive an additive migration and backup.

Railway serves the Python WSGI app with Gunicorn 27.0.1, one worker/four threads,
one replica, and idle sleep enabled. SQLite is stored on the attached /data
volume. See PUBLIC-DEPLOYMENT.md and docs/public-verification.json for the
verified public address and restart checks. No paid-plan upgrade was performed.

The refreshed PDF/DOCX contains all five E-R panels, the 18 relations, five main
query outcomes, and current-build interface illustrations. Capture provenance is
in docs/current-web-screenshots/README.md. Team participation still needs final
confirmation; older CLI figures remain supplementary evidence.
