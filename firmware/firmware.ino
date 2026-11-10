/**
 * ==============================================================================
 * Classroom Posture Monitor — ESP32-CAM MJPEG Stream Firmware
 * Role: TV1 (Hardware & Network Video Stream)
 * Hardware: AI-Thinker ESP32-CAM (OV2640, PSRAM 4MB)
 * Protocol: HTTP Streaming (multipart/x-mixed-replace)
 * ==============================================================================
 */

#include "esp_camera.h"
#include <WiFi.h>
#include "esp_http_server.h"
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

#include "camera_pins.h"

// Wi-Fi Configuration
#if __has_include("secrets.h")
#include "secrets.h"
#else
#include "secrets.example.h"
#endif

// HTTP Streaming Constants
#define PART_BOUNDARY "123456789000000000000987654321"
static const char* _STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* _STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char* _STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

httpd_handle_t stream_httpd = NULL;
unsigned long last_wifi_reconnect_attempt = 0;
const unsigned long WIFI_RECONNECT_INTERVAL_MS = 5000;

// Frame rate tracking
static unsigned long frame_count = 0;
static unsigned long last_fps_calc_time = 0;
static float current_fps = 0.0;

// Set to true when sensor does not support hardware JPEG (e.g. OV7670).
// stream_handler will then run software JPEG encoding via frame2jpg().
static bool g_use_software_jpeg = false;
static uint16_t g_sensor_pid = 0;
static bool g_is_client_connected = false;
static float g_raw_hardware_fps = 0.0;

/**
 * @brief MJPEG Stream Request Handler
 * Streams JPEG frames continuously to connected client (OpenCV / Browser).
 */
/**
 * @brief MJPEG Stream Request Handler with Frame Rate Pacing & Single-Chunk TCP
 * Locks framerate to a steady 10.0 FPS to eliminate erratic jitter (4-13 FPS).
 */
static esp_err_t stream_handler(httpd_req_t *req) {
    camera_fb_t *fb        = NULL;
    esp_err_t    res       = ESP_OK;
    size_t       _jpg_buf_len = 0;
    uint8_t     *_jpg_buf  = NULL;
    char         part_buf[128];
    bool         jpg_allocated = false;

    res = httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);
    if (res != ESP_OK) return res;
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    httpd_resp_set_hdr(req, "X-Framerate", "10");

    Serial.println("[HTTP] Client connected to /stream");
    digitalWrite(LED_BUILTIN_PIN, LOW);
    g_is_client_connected = true;

    // Target 10 FPS = exactly 100ms per frame budget
    const unsigned long TARGET_FRAME_TIME_MS = 100;

    while (true) {
        unsigned long frame_start_time = millis();

        fb = esp_camera_fb_get();
        if (!fb) {
            Serial.println("[CAM] Camera capture failed");
            res = ESP_FAIL;
            break;
        }

        jpg_allocated = false;

        if (fb->format == PIXFORMAT_JPEG) {
            // Hardware JPEG
            _jpg_buf_len = fb->len;
            _jpg_buf     = fb->buf;
        } else {
            // Software JPEG: Quality 60 for ultra-fast, consistent CPU compression time (~65ms)
            bool ok = frame2jpg(fb, 60, &_jpg_buf, &_jpg_buf_len);
            esp_camera_fb_return(fb);
            fb = NULL;
            if (!ok) {
                Serial.println("[CAM] Software JPEG encode failed");
                res = ESP_FAIL;
                break;
            }
            jpg_allocated = true;
        }

        // Send Boundary + Header in one single chunk to cut TCP socket overhead
        size_t hlen = snprintf(part_buf, sizeof(part_buf),
                              "\r\n--" PART_BOUNDARY "\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n",
                              _jpg_buf_len);
        res = httpd_resp_send_chunk(req, part_buf, hlen);

        // Send JPEG image data
        if (res == ESP_OK) {
            res = httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len);
        }

        if (jpg_allocated) {
            free(_jpg_buf);
        }
        if (fb) {
            esp_camera_fb_return(fb);
            fb = NULL;
        }
        _jpg_buf = NULL;

        if (res != ESP_OK) break;

        // Frame Rate Tracking
        frame_count++;
        unsigned long now = millis();
        if (now - last_fps_calc_time >= 1000) {
            current_fps    = (frame_count * 1000.0f) / (now - last_fps_calc_time);
            frame_count    = 0;
            last_fps_calc_time = now;
        }

        // Frame Pacer: Sleep remainder of 100ms budget to guarantee rock-solid steady FPS
        unsigned long elapsed = millis() - frame_start_time;
        if (elapsed < TARGET_FRAME_TIME_MS) {
            delay(TARGET_FRAME_TIME_MS - elapsed);
        }
    }

    g_is_client_connected = false;
    current_fps = 0.0;
    digitalWrite(LED_BUILTIN_PIN, HIGH);
    Serial.println("[HTTP] Client disconnected from /stream");
    return res;
}

/**
 * @brief System Status / Health Check Handler
 * Returns device metrics in JSON format.
 */
static esp_err_t status_handler(httpd_req_t *req) {
    httpd_resp_set_type(req, "application/json");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

    char json_response[384];
    snprintf(json_response, sizeof(json_response),
        "{"
        "\"device\":\"ESP32-CAM\","
        "\"status\":\"ONLINE\","
        "\"stream_endpoint\":\"/stream\","
        "\"ip\":\"%s\","
        "\"resolution\":\"%s\","
        "\"wifi_rssi\":%d,"
        "\"streaming_fps\":%.1f,"
        "\"raw_hardware_fps\":%.1f,"
        "\"client_connected\":%s,"
        "\"sensor_pid\":\"0x%04X\","
        "\"free_heap\":%u,"
        "\"free_psram\":%u,"
        "\"uptime_sec\":%lu"
        "}",
        WiFi.localIP().toString().c_str(),
        g_use_software_jpeg ? "320x240" : "640x480",
        WiFi.RSSI(),
        current_fps,
        g_raw_hardware_fps,
        g_is_client_connected ? "true" : "false",
        g_sensor_pid,
        ESP.getFreeHeap(),
        ESP.getFreePsram(),
        millis() / 1000
    );

    return httpd_resp_send(req, json_response, strlen(json_response));
}

/**
 * @brief Web UI Handler for root "/"
 * Serves an attractive HTML viewer that scales up the camera stream to 800px wide.
 */
static esp_err_t index_handler(httpd_req_t *req) {
    httpd_resp_set_type(req, "text/html");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

    static const char PROGMEM INDEX_HTML[] =
        "<!DOCTYPE html>"
        "<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>ESP32-CAM Live Stream</title>"
        "<style>"
        "body{background:#121214;color:#f0f0f0;font-family:system-ui,-apple-system,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;padding:15px;box-sizing:border-box}"
        ".card{background:#1e1e24;padding:24px;border-radius:18px;box-shadow:0 12px 35px rgba(0,0,0,0.6);text-align:center;max-width:850px;width:100%}"
        "h2{margin:0 0 16px;font-size:22px;color:#00e676;letter-spacing:0.5px}"
        ".viewport{width:100%;background:#0a0a0c;border-radius:12px;overflow:hidden;border:2px solid #2e2f38}"
        "img{width:100%;max-width:800px;height:auto;display:block;margin:0 auto;image-rendering:auto}"
        ".footer{margin-top:16px;display:flex;justify-content:center;gap:12px;flex-wrap:wrap}"
        ".badge{background:#2b2c36;padding:6px 14px;border-radius:20px;font-size:13px;color:#9e9ea7}"
        ".badge b{color:#00e676}"
        "</style></head>"
        "<body><div class='card'>"
        "<h2>Classroom Posture Monitor — Live Camera</h2>"
        "<div class='viewport'><img src='/stream' alt='Live Video Stream'></div>"
        "<div class='footer'>"
        "<span class='badge'>Stream: <b>ONLINE</b></span>"
        "<span class='badge'>Resolution: <b>320x240 (Scaled)</b></span>"
        "<span class='badge'>Paced FPS: <b>10.0 FPS</b></span>"
        "<span class='badge'>Raw JSON: <a href='/status' style='color:#64b5f6'>/status</a></span>"
        "</div></div></body></html>";

    return httpd_resp_send(req, INDEX_HTML, strlen(INDEX_HTML));
}

/**
 * @brief Initialize and start the HTTP server
 */
void startCameraServer() {
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = 80;
    config.ctrl_port = 32768;
    config.max_open_sockets = 4;

    httpd_uri_t index_uri = {
        .uri       = "/",
        .method    = HTTP_GET,
        .handler   = index_handler,
        .user_ctx  = NULL
    };

    httpd_uri_t stream_uri = {
        .uri       = "/stream",
        .method    = HTTP_GET,
        .handler   = stream_handler,
        .user_ctx  = NULL
    };

    httpd_uri_t status_uri = {
        .uri       = "/status",
        .method    = HTTP_GET,
        .handler   = status_handler,
        .user_ctx  = NULL
    };

    Serial.printf("[HTTP] Starting web server on port: '%d'\n", config.server_port);
    if (httpd_start(&stream_httpd, &config) == ESP_OK) {
        httpd_register_uri_handler(stream_httpd, &index_uri);
        httpd_register_uri_handler(stream_httpd, &stream_uri);
        httpd_register_uri_handler(stream_httpd, &status_uri);
        Serial.println("[HTTP] Camera stream server started successfully");
    } else {
        Serial.println("[HTTP] Failed to start HTTP server!");
    }
}

/**
 * @brief Initialize camera with automatic sensor detection.
 *
 * Strategy (2-phase, single deinit):
 *   Phase 1 — Probe:  GRAYSCALE + PSRAM, 10MHz.
 *                     Works with ALL sensor types (OV2640, OV7670, OV7725…).
 *                     Reads sensor PID.
 *   Phase 2 — Config: Deinit + reinit with optimal format for the detected sensor.
 *     • OV2640 (PID=0x2642): JPEG + PSRAM double-buffer — hardware encoding, full speed.
 *     • Other  (OV7670 etc): RGB565 + PSRAM single-buffer — software JPEG in stream_handler.
 *
 * Why 2-phase instead of trying JPEG first:
 *   "JPEG format is not supported on this sensor" (0x106) is thrown when the sensor PID
 *   does not match OV2640 — which happens both when the cable is loose AND when the
 *   sensor is literally not OV2640. The probe phase distinguishes the two cases.
 */
bool initCamera() {
    // ── Pin mapping (AI-Thinker ESP32-CAM) ──────────────────────────────────
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer   = LEDC_TIMER_0;
    config.pin_d0       = Y2_GPIO_NUM;
    config.pin_d1       = Y3_GPIO_NUM;
    config.pin_d2       = Y4_GPIO_NUM;
    config.pin_d3       = Y5_GPIO_NUM;
    config.pin_d4       = Y6_GPIO_NUM;
    config.pin_d5       = Y7_GPIO_NUM;
    config.pin_d6       = Y8_GPIO_NUM;
    config.pin_d7       = Y9_GPIO_NUM;
    config.pin_xclk     = XCLK_GPIO_NUM;
    config.pin_pclk     = PCLK_GPIO_NUM;
    config.pin_vsync    = VSYNC_GPIO_NUM;
    config.pin_href     = HREF_GPIO_NUM;
    config.pin_sccb_sda = SIOD_GPIO_NUM;
    config.pin_sccb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn     = PWDN_GPIO_NUM;
    config.pin_reset    = RESET_GPIO_NUM;

    // ── Phase 1: Sensor probe (GRAYSCALE works for every sensor type) ────────
    Serial.println("[CAM] Phase 1: Probing sensor with GRAYSCALE + 10MHz...");
    config.xclk_freq_hz = 10000000;
    config.pixel_format = PIXFORMAT_GRAYSCALE;
    config.frame_size   = FRAMESIZE_QQVGA; // 160x120 — smallest, fastest probe
    config.jpeg_quality = 12;
    config.fb_count     = 1;
    // Always use PSRAM for probe so DMA malloc never fails even after a deinit
    config.fb_location  = psramFound() ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;
    config.grab_mode    = CAMERA_GRAB_WHEN_EMPTY;

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("[CAM] Probe failed (0x%x) — cannot communicate with sensor at all.\n", err);
        Serial.println("[CAM] *** This is a HARDWARE / CABLE problem ***");
        Serial.println("[CAM]   • Check FPC ribbon cable: gold contacts face DOWN into connector.");
        Serial.println("[CAM]   • Make sure the black plastic latch is fully closed/locked.");
        Serial.println("[CAM]   • Try unplugging and re-plugging USB power, then press RST.");
        return false;
    }

    // ── Read sensor PID & Hardware Capabilities ─────────────────────────────
    sensor_t *s = esp_camera_sensor_get();
    uint8_t pid = s ? s->id.PID : 0;
    uint8_t ver = s ? s->id.VER : 0;
    uint8_t midh = s ? s->id.MIDH : 0;
    uint8_t midl = s ? s->id.MIDL : 0;
    g_sensor_pid = pid;

    Serial.println("\n========================================================");
    Serial.println("            HARDWARE SENSOR DIAGNOSTIC REPORT           ");
    Serial.println("========================================================");
    Serial.printf("  Product ID (PID)      : 0x%02X\n", pid);
    Serial.printf("  Version Register (VER): 0x%02X\n", ver);
    Serial.printf("  Manufacturer ID (MID) : 0x%02X%02X\n", midh, midl);

    bool hw_jpeg_capable = false;
    const char *sensor_name = "Unknown Sensor";

    if (pid == 0x26) {
        sensor_name = "OmniVision OV2640 (2 Megapixel)";
        hw_jpeg_capable = true;
    } else if (pid == 0x76) {
        sensor_name = "OmniVision OV7670 (VGA 0.3 Megapixel)";
        hw_jpeg_capable = false;
    } else if (pid == 0x77) {
        sensor_name = "OmniVision OV7725 (VGA 0.3 Megapixel)";
        hw_jpeg_capable = false;
    } else if (pid == 0x36) {
        sensor_name = "OmniVision OV3660 (3 Megapixel)";
        hw_jpeg_capable = true;
    } else if (pid == 0x56) {
        sensor_name = "OmniVision OV5640 (5 Megapixel)";
        hw_jpeg_capable = true;
    }

    Serial.printf("  Detected Model        : %s\n", sensor_name);
    Serial.printf("  Hardware JPEG Support : %s\n", hw_jpeg_capable ? "YES (Hardware Engine Available)" : "NO (Raw Pixels Only - Software Emulation)");
    Serial.println("========================================================\n");

    // ── Phase 2: Reinit with optimal format for detected sensor ─────────────
    esp_camera_deinit();
    delay(300); // allow full GPIO/DMA teardown before reinit

    if (hw_jpeg_capable) {
        // Hardware JPEG — optimal path (OV2640)
        config.pixel_format = PIXFORMAT_JPEG;
        config.xclk_freq_hz = 20000000;
        if (psramFound()) {
            config.frame_size   = FRAMESIZE_VGA; // 640×480
            config.jpeg_quality = 12;
            config.fb_count     = 2;             // dual-buffer for max FPS
            config.fb_location  = CAMERA_FB_IN_PSRAM;
            config.grab_mode    = CAMERA_GRAB_LATEST;
            Serial.println("[CAM] Mode: Hardware JPEG VGA 640x480 + 20MHz (Target: 20-25 FPS)");
        } else {
            config.frame_size   = FRAMESIZE_CIF;
            config.jpeg_quality = 14;
            config.fb_count     = 1;
            config.fb_location  = CAMERA_FB_IN_DRAM;
            config.grab_mode    = CAMERA_GRAB_WHEN_EMPTY;
            Serial.println("[CAM] Mode: Hardware JPEG CIF (No PSRAM)");
        }
        g_use_software_jpeg = false;
    } else {
        // Non-JPEG Sensor (OV7670, etc.) — Optimized Goldilocks Mode
        config.pixel_format = PIXFORMAT_RGB565;
        config.xclk_freq_hz = 16000000;          // Boost sensor scan clock to 16MHz
        config.frame_size   = FRAMESIZE_QVGA;    // 320x240 (Optimal Goldilocks Resolution, 4:3)
        config.jpeg_quality = 12;
        config.fb_count     = 2;
        config.fb_location  = psramFound() ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;
        config.grab_mode    = CAMERA_GRAB_LATEST;
        g_use_software_jpeg = true;
        Serial.println("[CAM] Mode: Goldilocks Software JPEG QVGA 320x240 + 16MHz (Target: 8-10 FPS)");
    }

    err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("[CAM] Phase 2 init failed: 0x%x\n", err);
        return false;
    }

    // Fine-tune sensor image quality
    s = esp_camera_sensor_get();
    if (s != NULL) {
        s->set_vflip(s, 0);      // set 1 if image is upside-down
        s->set_hmirror(s, 1);    // 1 = flip horizontal (mirror)
        s->set_brightness(s, 1); // -2 to 2
        s->set_contrast(s, 1);   // -2 to 2
    }

    Serial.printf("[CAM] Camera ready! Software JPEG: %s\n",
                  g_use_software_jpeg ? "YES (OV7670/other)" : "NO (OV2640 hw)");
    return true;
}

/**
 * @brief Benchmark raw camera sensor capture speed without network overhead.
 * Captures sample_frames consecutive frames in a tight loop and calculates hardware FPS.
 */
float benchmarkSensorFPS(int sample_frames = 30) {
    Serial.println("\n--------------------------------------------------------");
    Serial.printf("[BENCHMARK] Running hardware raw capture test (%d frames)...\n", sample_frames);

    // Warm-up 2 frames to flush the camera DMA pipeline
    for (int i = 0; i < 2; i++) {
        camera_fb_t *warmup_fb = esp_camera_fb_get();
        if (warmup_fb) esp_camera_fb_return(warmup_fb);
    }

    unsigned long start_time = millis();
    int frames_captured = 0;
    size_t total_bytes = 0;

    for (int i = 0; i < sample_frames; i++) {
        camera_fb_t *fb = esp_camera_fb_get();
        if (fb) {
            frames_captured++;
            total_bytes += fb->len;
            esp_camera_fb_return(fb);
        }
    }
    unsigned long duration_ms = millis() - start_time;
    if (duration_ms == 0) duration_ms = 1;

    float raw_fps = (frames_captured * 1000.0f) / duration_ms;
    float avg_frame_kb = frames_captured > 0 ? (total_bytes / 1024.0f) / frames_captured : 0;
    float bandwidth_mbps = (total_bytes * 8.0f) / (duration_ms * 1000.0f);

    Serial.printf("[BENCHMARK] Raw Hardware FPS  : %.2f FPS\n", raw_fps);
    Serial.printf("[BENCHMARK] Total Time Taken  : %lu ms (%d frames)\n", duration_ms, frames_captured);
    Serial.printf("[BENCHMARK] Avg JPEG Size     : %.1f KB per frame\n", avg_frame_kb);
    Serial.printf("[BENCHMARK] Data Throughput   : %.2f Mbps\n", bandwidth_mbps);
    Serial.println("--------------------------------------------------------\n");

    return raw_fps;
}

/**
 * @brief Connect to Wi-Fi with non-sleeping mode
 */
void connectWiFi() {
    Serial.printf("[WiFi] Connecting to SSID: %s\n", WIFI_SSID);
    WiFi.mode(WIFI_STA);

    // Disable Wi-Fi sleep mode to keep network ping jitter < 30ms
    WiFi.setSleep(false);

    WiFi.begin(WIFI_SSID, WIFI_PASS);

    unsigned long start_attempt = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - start_attempt < 15000) {
        delay(250);
        digitalWrite(LED_BUILTIN_PIN, !digitalRead(LED_BUILTIN_PIN)); // Blink LED
        Serial.print(".");
    }
    Serial.println();

    if (WiFi.status() == WL_CONNECTED) {
        digitalWrite(LED_BUILTIN_PIN, HIGH); // LED off when connected (Active LOW)
        Serial.println("[WiFi] Connected successfully!");
        Serial.printf("[WiFi] IP Address: http://%s\n", WiFi.localIP().toString().c_str());
        Serial.printf("[WiFi] Stream URL: http://%s/stream\n", WiFi.localIP().toString().c_str());
        Serial.printf("[WiFi] RSSI Signal: %d dBm\n", WiFi.RSSI());
    } else {
        Serial.println("[WiFi] Connection FAILED. Check credentials or AP availability.");
    }
}

void setup() {
    // 1. Disable brownout detector to prevent reboot on Wi-Fi current spikes (~500mA)
    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);

    // 2. Initialize Status Pins
    pinMode(LED_BUILTIN_PIN, OUTPUT);
    digitalWrite(LED_BUILTIN_PIN, HIGH); // Off initially (Active LOW)

    pinMode(LED_FLASH_PIN, OUTPUT);
    digitalWrite(LED_FLASH_PIN, LOW);    // Flash LED off

    // 3. Initialize Serial Interface
    Serial.begin(115200);
    delay(1000);
    Serial.println("\n========================================================");
    Serial.println("  Classroom Posture Monitor — ESP32-CAM Video Streamer  ");
    Serial.println("========================================================");

    // 4. Initialize Camera Hardware
    if (!initCamera()) {
        Serial.println("[FATAL] Camera hardware initialization failed! Halting.");
        while (true) {
            // Blink rapidly to indicate hardware error
            digitalWrite(LED_BUILTIN_PIN, LOW);
            delay(100);
            digitalWrite(LED_BUILTIN_PIN, HIGH);
            delay(100);
        }
    }

    // 5. Measure Pure Hardware Sensor FPS (Benchmark without network)
    g_raw_hardware_fps = benchmarkSensorFPS(30);

    // 6. Connect to Local Wi-Fi
    connectWiFi();

    // 7. Start HTTP Streaming Server
    startCameraServer();

    Serial.println("[SYSTEM] Ready. Waiting for AI Vision client connection...");
}

void loop() {
    unsigned long now = millis();

    // 1. Handle Wi-Fi auto-reconnection non-blockingly
    if (WiFi.status() != WL_CONNECTED) {
        if (now - last_wifi_reconnect_attempt >= WIFI_RECONNECT_INTERVAL_MS) {
            last_wifi_reconnect_attempt = now;
            Serial.println("[WiFi] Disconnected! Attempting auto-reconnect...");
            WiFi.reconnect();
        }
    }

    // 2. Periodic FPS & Telemetry Reporting on Serial Monitor every 2 seconds
    static unsigned long last_telemetry_print = 0;
    if (now - last_telemetry_print >= 2000) {
        last_telemetry_print = now;
        if (g_is_client_connected) {
            Serial.printf("[TELEMETRY] Streaming FPS: %.1f | Wi-Fi RSSI: %d dBm | Free PSRAM: %u KB | Free Heap: %u KB\n",
                          current_fps,
                          WiFi.RSSI(),
                          ESP.getFreePsram() / 1024,
                          ESP.getFreeHeap() / 1024);
        } else {
            Serial.printf("[TELEMETRY] Idle (No Client) | Hardware Capability: %.1f FPS | Wi-Fi RSSI: %d dBm\n",
                          g_raw_hardware_fps,
                          WiFi.RSSI());
        }
    }

    delay(100);
}
