# Expected Fixtures

JSON files in this directory contain expected analysis output for the PGN fixtures in
`../pgn/`. They are used by worker integration tests to verify that the analysis pipeline
produces deterministic, correct classifications.

## Format

Each file is named after the corresponding PGN fixture (e.g. `simple_game.json` for
`simple_game.pgn`). Structure:

```json
{
  "engine_depth": 5,
  "moves": [
    {
      "ply": 1,
      "san": "e4",
      "classification": "best"
    }
  ]
}
```

## Updating Fixtures

Run `scripts/update_fixtures.sh` after changing engine settings or analysis logic.
Review the diff carefully before committing — unexpected changes indicate a regression.
