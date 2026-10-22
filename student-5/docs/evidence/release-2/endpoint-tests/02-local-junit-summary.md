### Student 5 post-commit endpoint tests (POST and PUT /api/destinations)

| Test | Result |
|---|---|
| `test_endpoints_cicd::test_create_destination_returns_201_with_the_stored_row` | pass |
| `test_endpoints_cicd::test_create_destination_relays_database_400_for_invalid_input[empty-body]` | pass |
| `test_endpoints_cicd::test_create_destination_relays_database_400_for_invalid_input[missing-visa-requirement]` | pass |
| `test_endpoints_cicd::test_create_destination_relays_database_400_for_invalid_input[blank-country]` | pass |
| `test_endpoints_cicd::test_create_destination_with_non_json_body_relays_database_400` | pass |
| `test_endpoints_cicd::test_create_destination_returns_503_when_database_is_down` | pass |
| `test_endpoints_cicd::test_update_destination_forwards_only_supplied_fields_and_returns_200` | pass |
| `test_endpoints_cicd::test_update_destination_relays_database_400_for_invalid_input[blank-visa-requirement]` | pass |
| `test_endpoints_cicd::test_update_destination_relays_database_400_for_invalid_input[non-string-country]` | pass |
| `test_endpoints_cicd::test_update_unknown_destination_relays_database_404` | pass |
| `test_endpoints_cicd::test_update_destination_with_non_integer_id_is_404_without_database_call` | pass |
| `test_endpoints_cicd::test_update_destination_returns_503_when_database_is_down[connection-refused]` | pass |
| `test_endpoints_cicd::test_update_destination_returns_503_when_database_is_down[read-timeout]` | pass |

**13 of 13 passed**

