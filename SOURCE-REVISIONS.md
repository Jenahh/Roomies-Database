# Integration sources

## Railway deployment preparation

- Dockerfile fetches the same fixed app revision a294a7e4b2903a76be7d9a4319bf6a57825a8eae
  in an isolated build stage. The final image contains compiled assets, not the
  app source or its Git checkout. The separate repository remains unchanged.
- Hosted server: Gunicorn 27.0.1, one worker with four threads; existing WSGI
  application and relational database operations are reused.
- start_hosted.py requires Railway's attached volume and validates the complete
  SQL-connected build before starting. No fallback to ephemeral SQLite storage.
- Railway deployment and public URL verification are pending account connection.
- See RAILWAY-SETUP.md for usage limits and acceptance checks.

- Database: Jenahh/Roomies-Database add-entities-and-queries, b73fa25.
- Existing Python API contract: Jenahh/Roomies, a08383b.
- This change adds and tests the expanded Python API and CLI inside the CSC 4402 repository only.
- No frontend files are copied, modified, or required to run the standalone CLI.
- Existing Roomies web chores and request screens can optionally use this server on localhost:8765.
- Report files are review drafts: complete and confirm individual contributions before submission.

## Local Honors preview (not deployed)

- Branch: honors-local-preview, starting from CSC4402 dev c30e69a.
- Current local frontend: Jenahh/Roomies a294a7e (roomies-github-current).
  The earlier a08383b build remains compatible with the original API contract.
- The original app's tracked source is not modified or copied into this repo.
  The preview serves its generated dist files directly from the separate checkout.
- Expanded web forms are implemented in web/ and call the same scoped SQL
  operations as manage.py. The old HTTP server and the new WSGI entry point
  share a single JSON dispatcher to preserve the original app's API contract.
- Default working database: demo-local-honors.sqlite3, created only if absent;
  the supplied submission database is not modified.
- The existing report PDF and DOCX remain unchanged during preview development.
  Update interface illustrations and hosting details after review/deployment.
- The mobile preview shell embeds the existing build on the same origin and
  adds a CSC4402-only response adapter (web/app-bridge.js and .css) for demo
  login, shared navigation, and routing bill entry points to SQL-backed forms.
  These additions are inserted only into HTML requested for embedding and are
  never written into the separate frontend checkout or its build files.
- The ordinary-build fallback refreshes the original Home display cache from
  SQLite. The newer SQL expense build instead replaces the ledger hook and its
  identity argument in memory; both Home and the reused ExpensesScreen read
  and write the relational ledger directly.
- Residents use Home, Chores, Bills, Calendar, and Profile directly from the
  main bar. Additional database operations are secondary under Details.
  The header uses the original Roomies Logo.png, copied without image editing.
- ExpenseDetail, ExpenseRecurrence and ExpensePayment extend the local schema;
  the supplied database has 18 tables with the original 15 tables' seed rows
  preserved. Older working databases receive an additive migration and backup.
- The build helper writes only compiled browser assets into web/roomies. It
  does not edit the app checkout or its normal dist. The original expense UI,
  recurrence expansion and settlement algorithms are reused without copying
  their source. See docs/EXPENSE-INTEGRATION.md and ER extension E.
