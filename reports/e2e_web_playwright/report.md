# Web E2E Playwright report

- Overall: **PASS**
- Run time (UTC): 2026-11-18T16:56:34+00:00
- Method: Playwright Python driving headless Microsoft Edge from terminal; this is browser automation, not physical screen operation.
- Data: synthetic events only; all seat identifiers use `TEST-` prefix.
- Screenshots: 10 real browser image(s) in `screenshots/`.
- Logs: [`browser_logs.jsonl`](browser_logs.jsonl); API query values and response bodies are omitted.

| Case | Result | Detail |
| --- | --- | --- |
| `test_empty_dashboard_four_labels_and_w1_freshness` | PASSED |  |
| `test_filters_timezone_reverse_range_and_eight_row_pagination` | PASSED |  |
| `test_http_400_proxy_502_and_recovery` | PASSED |  |
| `test_html_payload_is_text_and_never_creates_elements_or_runs_script` | PASSED |  |
| `test_camera_url_validation_preview_stop_timeout_and_no_api_upload` | PASSED |  |
| `test_polling_request_count_over_a_defined_ten_second_window` | PASSED |  |

## Polling measurement

The polling case starts a 10-second window after the dashboard has loaded and its initial API responses have settled. It records browser requests whose URL path begins `/api/`, including both latest and history endpoints. The initial page-load requests are outside that window; interval requests landing on the window boundaries are included by monotonic timestamps. The test checks a range rather than expecting exactly five requests.

```json
{
  "window_seconds": 10.012,
  "api_requests": 10,
  "by_endpoint": {
    "/api/events": 5,
    "/api/events/latest": 5
  },
  "boundary_policy": "monotonic timestamps inclusive at both boundaries; page-load requests before window excluded"
}
```

## Limits

The camera fixture is synthetic and local. It verifies the browser image control path and request isolation; it does not verify ESP32 hardware, real MJPEG timing, or classroom imagery.
