# Backend (TV3)

Backend sử dụng Python standard-library HTTP server, PostgreSQL, Paho MQTT và Psycopg 3.

## Run locally

From the repository root, copy `.env.example` to `.env`. The database uses `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD`; Compose maps the same name/user/password values into PostgreSQL. `DB_URL` is an optional override and its username/password must be URL-encoded. A password containing `$` in `.env` must be single-quoted for Compose. Install runtime dependencies with `python -m pip install -r backend/requirements.txt`.

For local Python processes, start PostgreSQL and the broker with `docker compose up -d postgres mqtt-broker`. Start the API with `python -m backend.api`. In another terminal start the subscriber with `python -m backend.mqtt_subscriber`. The API listens on `http://localhost:8000`; the database is configured by `DB_URL`. Do not run a second subscriber with the same MQTT client ID while the Compose subscriber is running.

The full Compose stack runs the API and subscriber as separate services. The `dashboard` service runs `web/app_web.py` on port 8080 and proxies `/api/` to the API service, so browser requests stay same-origin. `BACKEND_URL` is set to `http://api:8000` and `WEB_PORT` to `8080` in Compose. The API is also published at `http://localhost:8000` for direct checks. Keep the broker bound to loopback during local development.

To run the dashboard locally from the repository root without Docker:

```powershell
$env:BACKEND_URL = "http://localhost:8000"
$env:WEB_PORT = "8080"
python web/app_web.py
```

Open `http://localhost:8080`. The API process must already be reachable at `BACKEND_URL`.

Check the API with `Invoke-RestMethod http://localhost:8000/api/events/latest` or `Invoke-RestMethod 'http://localhost:8000/api/events?limit=20'`.

## Layout

The backend is split into layers (`config`, `domain`, `infrastructure`, `repositories`, `services`, `interfaces`) with dependencies pointing downwards only; `api.py` and `mqtt_subscriber.py` are thin entry points. See [ARCHITECTURE.md](ARCHITECTURE.md) for responsibilities and where to add new features. Run entry points from the repository root with `python -m backend.api` and `python -m backend.mqtt_subscriber` (running `python backend/api.py` directly is no longer supported).

## API

- `GET /api/events/latest`: latest stored event for each seat.
- `GET /api/events?from=<UTC>&to=<UTC>&seat_id=<code>&limit=<n>`: filtered history. Times must be ISO-8601 UTC; use `Z` in query strings, or percent-encode the `+` in `+00:00` as `%2B`. `limit` defaults to 100 and is capped at 500.

Responses contain JSON arrays with `event_id`, `ts`, `seat_id`, `label`, `trunk_angle`, `confidence`, and `model_version`. PostgreSQL stores timestamps as `TIMESTAMPTZ`; API responses serialize them in UTC.

The API uses `API_DB_CONNECT_TIMEOUT` for database connections made by GET queries. It defaults to 2 seconds and accepts integer values from 1 through 30; invalid values stop API startup with a clear configuration error. This API-only setting does not change the subscriber's 5-second database connection timeout or its bounded ingest retry behavior. Unsupported methods on a known API path return HTTP 405 with JSON `{"error":"Method not allowed"}` and `Allow: GET`. An unknown path remains HTTP 404 with the existing JSON error; the API does not provide write methods.

## Validation and privacy

The subscriber rejects malformed, oversized, deeply nested, extra-field, invalid-label and invalid-value events. UUIDs are normalized before insert so equivalent textual UUID forms deduplicate. Duplicate `event_id` values are ignored by PostgreSQL's unique constraint. Raw frames and images are never written. Logs omit event contents and query strings.

The main `docker-compose.yml` creates `/mosquitto/data/password_file` from the main stack's `MQTT_USERNAME` and `MQTT_PASSWORD` environment values at broker startup, then sets owner `mosquitto:mosquitto` and mode `0600`. `mosquitto.conf` points to this file, and the directory is a named persistent volume. Running `docker compose down -v` on the main project deletes that volume: saved broker sessions/queued messages are lost, and the password file is recreated from the current environment on the next start. The same command also deletes the project's PostgreSQL volume and its event data. Do not run it on the main project without confirming database backups and that the broker credentials are available to recreate the password file; prefer plain `docker compose down` when preserving data. Recommend that the group document a backup/export and credential recovery procedure before anyone uses `down -v` on the main project.

## Event retention

Run `python -m backend.retention --days 30` to preview the number of rows eligible for deletion. `--days` overrides `RETENTION_DAYS`; one of them is required and must be between 1 and 3650. The CLI is dry-run by default. Deletion requires both `--apply` and `--confirm-db <database_name>`; the confirmation must exactly match the database selected by `DB_URL` or `DB_NAME`. Deletion is performed in batches of 1000 rows and logs aggregate counts only. There is no scheduled deletion.

Retention uses the event's source `ts` because the current schema has no `received_at`. A source clock that is ahead or behind can therefore change which rows qualify. The 30-day value is an example only and is not an approved project policy. Do not run `--apply` against a non-disposable database until the group approves retention.

## Seat calibration

From the repository root, install the Vision requirements, then run `python -m vision.tools.calibrate_seats --image path\to\approved\still.jpg` or set `CAM_STREAM_URL`/`VIDEO_FILE` and run `python -m vision.tools.calibrate_seats`. Drag to draw a rectangle and enter its anonymous `seat_id`; press `u` to undo, `c` to clear, `s` to save, or `q` to quit. By default the script prints a `seat_regions` YAML block. Add `--output path\to\regions.yaml` to write it to a separate file. Review and merge those bounds into `vision/config.yaml` manually; the script never edits that config.

## Limits / assumptions

PostgreSQL + Psycopg 3 is the selected stack for D-07. The dashboard uses polling as the proposed D-06 default. Connection status reflects API reachability only; camera/broker status semantics remain unresolved under D-04. The local Compose broker requires `MQTT_USERNAME` and `MQTT_PASSWORD`, disables anonymous access, and binds its ports to loopback. Keep credentials outside Git; shared environments must follow the approved broker access configuration.
