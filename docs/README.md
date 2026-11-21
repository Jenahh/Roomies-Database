# Report and evidence

- Roomies-CSC4402-Expanded-Report.pdf is the latest report draft (8 pages).
- Roomies-CSC4402-Expanded-Report.docx is its editable source. Check pagination after editing or re-exporting Word.
- Individual participation entries still require the team's actual responsibilities.
- Query screenshots show all 11 queries executed against a fresh SQLite seed in a native execution window. Cropping in the report removes unused space; full images are in query-screenshots/. query-results.json records the exact SQL and returned rows.
- The first five queries are the main rubric queries. Queries 6-11 are supplementary following feedback. Confirm the instructor's preferred treatment of supplementary queries before submission.
- Web screenshots are retained from the earlier demonstration. matching-request-evidence.sqlite3 is a separate fresh replay database verifying Request 1 = In Progress (Jordan, user 10) and Request 2 = Closed (Taylor, user 11), including RequestUpdate history. It is distinct from the root seed database, which starts both requests Open.
- Roomies-CLI-Interface-Illustrations.pdf and interface-*.txt provide larger CLI examples and original transcripts. The report uses shortened readable excerpts in five-cli-interfaces.png.
- Roomies-Expanded-ER-Diagrams.pdf and er-a through er-d contain the full-size diagram panels.

## Reproduce the executable checks
From the repository root:

```text
python roomies.py test
python -m unittest discover -v
python verify_demo.py
```

The report update changes documentation and evidence only. The SQLite application, schema, API and CLI are unchanged. The separate CSC 4330 repository is unchanged.
