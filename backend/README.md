# Backend (TV3)

Development backend using Python's standard-library HTTP server and PostgreSQL. The MQTT subscriber uses Paho MQTT; PostgreSQL access uses Psycopg 3.

## Run locally

From the repository root, copy `.env.example` to `.env`. The database uses `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD`; Compose maps the same name/user/password values into PostgreSQL. `DB_URL` is an optional override and its username/password must be URL-encoded. A password containing `$` in `.env` must be single-quoted for Compose. Install runtime dependencies with `python -m pip install -r backend/requirements.txt`. For tests, install `python -m pip install -r backend/requirements-dev.txt`.

For local Python processes, start PostgreSQL and the broker with `docker compose up -d postgres mqtt-broker`. Start the API with `python -m backend.api`. In another terminal start the subscriber with `python -m backend.mqtt_subscriber`. The API listens on `http://localhost:8000`; the database is configured by `DB_URL`. Do not run a second subscriber with the same MQTT client ID while the Compose subscriber is running.

The full Compose stack runs the API and subscriber as separate services. The dashboard is served by Nginx at `http://localhost:8080`, and Nginx proxies `/api/` to the API service, so browser requests stay same-origin. The API is also published at `http://localhost:8000` for direct checks. Do not expose the anonymous development broker to a shared or public network.

Publish sample messages from the repo root with `python tests/test_mock_publisher.py`. Check the API with `Invoke-RestMethod http://localhost:8000/api/events/latest` or `Invoke-RestMethod 'http://localhost:8000/api/events?limit=20'`.

## API

- `GET /api/events/latest`: latest stored event for each seat.
- `GET /api/events?from=<UTC>&to=<UTC>&seat_id=<code>&limit=<n>`: filtered history. Times must be ISO-8601 UTC; use `Z` in query strings, or percent-encode the `+` in `+00:00` as `%2B`. `limit` defaults to 100 and is capped at 500.

Responses contain JSON arrays with `event_id`, `ts`, `seat_id`, `label`, `trunk_angle`, `confidence`, and `model_version`. PostgreSQL stores timestamps as `TIMESTAMPTZ`; API responses serialize them in UTC. This implementation follows the proposed repository contract; confirm other open decisions before treating proposal values as final.

## Validation and privacy

The subscriber rejects malformed, oversized, deeply nested, extra-field, invalid-label and invalid-value events. UUIDs are normalized before insert so equivalent textual UUID forms deduplicate. Duplicate `event_id` values are ignored by PostgreSQL's unique constraint. Raw frames and images are never written. Logs omit event contents and query strings.

## Limits / assumptions

PostgreSQL + Psycopg 3 is the selected stack for D-07. The dashboard uses polling as the proposed D-06 default. Connection status reflects API reachability only; camera/broker status semantics remain unresolved under D-04. The broker's local development listener is anonymous and loopback-bound; shared environments require authenticated broker configuration and approved credentials outside Git.
