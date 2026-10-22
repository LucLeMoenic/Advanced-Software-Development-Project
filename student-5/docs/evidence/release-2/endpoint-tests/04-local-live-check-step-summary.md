### Student 5 live endpoint check (POST and PUT /api/destinations)

| Check | Result |
|---|---|
| POST /api/destinations valid -> 201 status=201 | pass |
| POST returns an id and the stored fields  | pass |
| POST missing visa_requirement -> 400 from the database status=400 | pass |
| Rejected POST stored nothing before=13 after=13 | pass |
| PUT /api/destinations/<id> valid -> 200 status=200 | pass |
| PUT merges the change and keeps the country  | pass |
| GET after PUT returns the updated row status=200 | pass |
| PUT blank visa_requirement -> 400 from the database status=400 | pass |
| Rejected PUT changed nothing  | pass |
| PUT unknown id -> 404 from the database status=404 | pass |
| Cleanup DELETE -> 204 status=204 | pass |
| Deleted destination is gone (404) status=404 | pass |
