const connection = document.querySelector('#connection');
const latestBox = document.querySelector('#seat-map');
const historyBox = document.querySelector('#history');
const form = document.querySelector('#filters');
const seatOptions = document.querySelector('#seat-options');
const cameraForm = document.querySelector('#camera-form');
const cameraInput = document.querySelector('#camera-url');
const cameraImage = document.querySelector('#camera-preview');
const cameraFrame = document.querySelector('#camera-frame');
const cameraStatus = document.querySelector('#camera-status');
const cameraHelp = document.querySelector('#camera-help');
const cameraStart = document.querySelector('#camera-start');
const cameraStop = document.querySelector('#camera-stop');
const pagePrevious = document.querySelector('#page-previous');
const pageNext = document.querySelector('#page-next');
const pageCaption = document.querySelector('#page-caption');
const freshnessStatus = document.querySelector('#freshness-status');
const PAGE_SIZE = 8;
const STALE_AFTER_SECONDS = 10; // Giả định UI theo nhịp Vision hiện tại; chưa phải quyết định occupancy.
const labelText = {upright: 'Thẳng', slouching: 'Cúi', leaning: 'Nghiêng', unknown: 'Chưa xác định'};
let activeFilters = {};
let inFlight = false;
let lastLatestSnapshot = '';
let lastHistorySnapshot = '';
let lastSeatOptionsSnapshot = '';
let historyItems = [];
let latestItems = [];
let latestReceivedAt = null;
let historyReceivedAt = null;
let lastRenderedFreshness = '';
let latestLoadError = '';
let historyLoadError = '';
let currentPage = 0;
let cameraConnectTimer = null;

function setText(selector, value) {
  document.querySelector(selector).textContent = value;
}

function formatTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : `${date.toLocaleString('vi-VN', {
    timeZone: 'Asia/Ho_Chi_Minh', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  })} GMT+7`;
}

function updateConnection(online) {
  connection.className = `connection ${online ? 'online' : 'offline'}`;
  connection.lastElementChild.textContent = online ? 'API đã phản hồi' : 'Không nhận được phản hồi API';
  setText('#api-metric', online ? 'Online' : 'Offline');
  setText('#api-caption', online ? 'Đã nhận phản hồi HTTP' : 'Lỗi mạng hoặc hết thời gian chờ');
}

async function getJson(path) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);
  try {
    const response = await fetch(path, {cache: 'no-store', signal: controller.signal});
    if (!response.ok) {
      const error = new Error(`HTTP ${response.status}`);
      error.status = response.status;
      throw error;
    }
    try {
      return await response.json();
    } catch (error) {
      error.status = response.status;
      throw error;
    }
  } finally {
    clearTimeout(timeout);
  }
}

function updatePostureCounts(items, nowMs) {
  const freshItems = items.filter(item => DashboardUtils.eventFreshness(item.ts, nowMs, STALE_AFTER_SECONDS).state === 'fresh');
  const counts = {upright: 0, slouching: 0, leaning: 0, unknown: 0};
  for (const item of freshItems) if (Object.hasOwn(counts, item.label)) counts[item.label] += 1;
  for (const [label, count] of Object.entries(counts)) {
    setText(`#count-${label}`, count);
    const meter = document.querySelector(`#count-${label}`).parentElement.querySelector('[role="meter"]');
    meter.setAttribute('aria-valuemax', Math.max(1, freshItems.length));
    meter.setAttribute('aria-valuenow', count);
    document.querySelector(`#bar-${label}`).style.width = freshItems.length ? `${count / freshItems.length * 100}%` : '0%';
  }
  setText('#seat-count', `${freshItems.length} / ${items.length}`);
}

function renderSeats(items, nowMs) {
  latestBox.replaceChildren();
  if (!items.length) {
    const empty = document.createElement('div'); empty.className = 'empty-state';
    const icon = document.createElement('span'); icon.className = 'empty-icon'; icon.textContent = '⌁';
    const title = document.createElement('strong'); title.textContent = 'Chưa có sự kiện';
    const message = document.createElement('p'); message.textContent = 'Dashboard không phân biệt được phòng trống với pipeline dừng.';
    empty.append(icon, title, message); latestBox.append(empty);
    return;
  }
  for (const event of items) {
    const freshness = DashboardUtils.eventFreshness(event.ts, nowMs, STALE_AFTER_SECONDS);
    const card = document.createElement('article');
    card.className = `seat-card posture-${event.label}${freshness.state === 'fresh' ? '' : ' seat-stale'}`;
    const icon = document.createElement('span'); icon.className = 'seat-icon'; icon.textContent = 'S';
    const details = document.createElement('div'); details.className = 'seat-details';
    const name = document.createElement('strong'); name.textContent = event.seat_id;
    const state = document.createElement('span'); state.className = 'seat-state'; state.textContent = labelText[event.label] || event.label;
    details.append(name, state);
    const angle = document.createElement('span'); angle.className = 'seat-angle';
    angle.textContent = DashboardUtils.formatAngle(event.trunk_angle);
    card.append(icon, details, angle);
    const time = document.createElement('span'); time.className = 'seat-time';
    const freshnessLabel = freshness.state === 'invalid' ? 'Thời gian sự kiện không hợp lệ' :
      freshness.state === 'future' ? 'Thời gian sự kiện ở tương lai' :
        freshness.state === 'stale' ? 'Lần cập nhật cuối' : 'Vị trí có dữ liệu mới';
    time.textContent = `${freshnessLabel} · ${formatTime(event.ts)}`;
    const date = new Date(event.ts);
    if (!Number.isNaN(date.getTime())) time.title = `${date.toISOString()} UTC`;
    card.append(time);
    latestBox.append(card);
  }
}

function renderEvents() {
  historyBox.replaceChildren();
  const pageCount = Math.max(1, Math.ceil(historyItems.length / PAGE_SIZE));
  currentPage = Math.min(currentPage, pageCount - 1);
  const start = currentPage * PAGE_SIZE;
  const pageItems = historyItems.slice(start, start + PAGE_SIZE);
  if (!pageItems.length) {
    historyBox.innerHTML = '<div class="empty-inline">Không có sự kiện phù hợp với bộ lọc.</div>';
  } else {
    for (const event of pageItems) {
      const row = document.createElement('article');
      row.className = `event-row posture-${event.label}`;
      const marker = document.createElement('span'); marker.className = 'event-marker';
      marker.textContent = event.label === 'upright' ? '✓' : event.label === 'unknown' ? '?' : '↗';
      const body = document.createElement('div'); body.className = 'event-body';
      const top = document.createElement('div'); top.className = 'event-topline';
      const label = document.createElement('strong'); label.textContent = labelText[event.label] || event.label;
      const seat = document.createElement('span'); seat.className = 'event-seat'; seat.textContent = event.seat_id;
      const timestamp = document.createElement('time'); timestamp.textContent = formatTime(event.ts);
      const date = new Date(event.ts);
      if (!Number.isNaN(date.getTime())) timestamp.title = `${date.toISOString()} UTC`;
      top.append(label, seat, timestamp);
      const meta = document.createElement('div'); meta.className = 'event-meta';
      const angle = event.trunk_angle == null ? 'Chưa có góc thân' : `Góc thân ${event.trunk_angle}°`;
      meta.textContent = `${angle} · Tin cậy ${Math.round(Number(event.confidence) * 100)}%`;
      const track = document.createElement('div'); track.className = 'confidence-track';
      const fill = document.createElement('span');
      fill.style.width = `${Math.max(0, Math.min(100, Number(event.confidence) * 100))}%`;
      track.append(fill);
      body.append(top, meta, track); row.append(marker, body); historyBox.append(row);
    }
  }
  pagePrevious.disabled = currentPage === 0;
  pageNext.disabled = currentPage >= pageCount - 1;
  pageCaption.textContent = `Trang ${currentPage + 1} / ${pageCount}`;
}

function updateHistoryCaption() {
  const start = currentPage * PAGE_SIZE;
  const visibleCount = Math.min(PAGE_SIZE, Math.max(0, historyItems.length - start));
  setText('#history-caption', `Hiển thị ${visibleCount} / ${historyItems.length} sự kiện gần đây đã tải`);
}

function updateFreshness(nowMs) {
  const summary = DashboardUtils.summarizeFreshness(latestItems, nowMs, STALE_AFTER_SECONDS);
  const status = summary.fresh === 0
    ? 'Chưa có dữ liệu mới. Dashboard không phân biệt được phòng trống với pipeline dừng.'
    : `${summary.fresh} / ${summary.total} vị trí có dữ liệu mới; ngưỡng cũ ${STALE_AFTER_SECONDS} giây.`;
  const apiIssue = latestLoadError ? ` Không tải được dữ liệu vị trí: ${latestLoadError}.` : '';
  const historyIssue = historyLoadError ? ` Không tải được lịch sử: ${historyLoadError}.` : '';
  const nextText = `${status}${apiIssue}${historyIssue}`;
  if (freshnessStatus.textContent !== nextText) freshnessStatus.textContent = nextText;
  const renderSignature = JSON.stringify(latestItems.map(item => [
    item, DashboardUtils.eventFreshness(item.ts, nowMs, STALE_AFTER_SECONDS).state,
  ]));
  if (renderSignature !== lastRenderedFreshness) {
    renderSeats(latestItems, nowMs);
    lastRenderedFreshness = renderSignature;
  }
  updatePostureCounts(latestItems, nowMs);
}

async function refresh() {
  if (inFlight || document.hidden) return;
  inFlight = true;
  try {
    const query = new URLSearchParams();
    if (activeFilters.seat_id) query.set('seat_id', activeFilters.seat_id);
    if (activeFilters.from) query.set('from', DashboardUtils.utcParam(activeFilters.from));
    if (activeFilters.to) query.set('to', DashboardUtils.utcParam(activeFilters.to));
    query.set('limit', '100');
    const responses = await Promise.allSettled([
      getJson('/api/events/latest'),
      getJson(`/api/events?${query}`),
    ]);
    const [latestResponse, historyResponse] = responses;
    const apiResponded = DashboardUtils.hasAvailableEndpoint(responses);
    updateConnection(apiResponded);
    const receivedAt = new Date();
    const previousLatestSnapshot = JSON.stringify(latestItems);
    const latestResult = DashboardUtils.applyEndpointResponse(
      {data: latestItems, receivedAt: latestReceivedAt}, latestResponse, receivedAt,
    );
    latestItems = latestResult.data;
    latestReceivedAt = latestResult.receivedAt;
    latestLoadError = latestResult.error;
    if (latestResponse.status === 'fulfilled') {
      const latestSnapshot = JSON.stringify(latestItems);
      if (latestSnapshot !== lastLatestSnapshot) lastLatestSnapshot = latestSnapshot;
      if (latestSnapshot !== previousLatestSnapshot) lastRenderedFreshness = '';
      setText('#seat-snapshot-caption', `Snapshot nhận lúc ${formatTime(latestReceivedAt)}`);
      const seatIds = [...new Set(latestItems.map(event => event.seat_id))].sort(DashboardUtils.compareSeatIds);
      const seatOptionsSnapshot = JSON.stringify(seatIds);
      if (seatOptionsSnapshot !== lastSeatOptionsSnapshot) {
        seatOptions.replaceChildren();
        for (const seatId of seatIds) {
          const option = document.createElement('option'); option.value = seatId; seatOptions.append(option);
        }
        lastSeatOptionsSnapshot = seatOptionsSnapshot;
      }
    }
    const historyResult = DashboardUtils.applyEndpointResponse(
      {data: historyItems, receivedAt: historyReceivedAt}, historyResponse, receivedAt,
    );
    const previousHistoryLoadError = historyLoadError;
    historyItems = historyResult.data;
    historyReceivedAt = historyResult.receivedAt;
    historyLoadError = historyResult.error;
    if (historyResponse.status === 'fulfilled') {
      const history = historyItems;
      const historySnapshot = JSON.stringify(history);
      if (historySnapshot !== lastHistorySnapshot) {
        historyItems = history;
        renderEvents();
        lastHistorySnapshot = historySnapshot;
      } else if (previousHistoryLoadError) {
        updateHistoryCaption();
      }
      setText('#event-count', history.length);
    } else {
      const snapshotTime = historyReceivedAt ? formatTime(historyReceivedAt) : 'chưa có snapshot';
      setText('#history-caption', `${historyLoadError}; đang giữ snapshot lịch sử nhận lúc ${snapshotTime}`);
    }
    updateFreshness(Date.now());
  } catch (error) {
    if (error instanceof RangeError) setText('#history-caption', 'Thời gian bộ lọc không hợp lệ.');
    else { updateConnection(Boolean(error.status)); console.error(error); }
  } finally {
    inFlight = false;
  }
}

function stopCamera(message = 'Đã ngắt kết nối') {
  clearTimeout(cameraConnectTimer);
  cameraImage.removeAttribute('src');
  cameraImage.hidden = true;
  cameraFrame.hidden = true;
  cameraStatus.textContent = message;
  cameraStatus.className = 'camera-status';
  cameraStart.disabled = false;
  cameraStop.disabled = true;
}

cameraForm.addEventListener('submit', event => {
  event.preventDefault();
  stopCamera('Đang kết nối…');
  let streamUrl;
  try {
    streamUrl = new URL(cameraInput.value.trim());
    if (streamUrl.protocol !== 'http:' || !streamUrl.hostname || streamUrl.username || streamUrl.password) {
      throw new Error('unsupported URL');
    }
  } catch {
    stopCamera('URL không hợp lệ');
    cameraHelp.textContent = 'Nhập URL HTTP hợp lệ, ví dụ http://192.168.1.105/stream. Không dùng HTTPS hoặc thông tin đăng nhập trong URL.';
    cameraInput.setAttribute('aria-invalid', 'true');
    return;
  }
  cameraInput.removeAttribute('aria-invalid');
  cameraHelp.textContent = 'Đang thử kết nối. Nếu không có hình, kiểm tra máy tính cùng mạng và URL /stream trên Serial Monitor.';
  cameraStatus.textContent = 'Đang kết nối…';
  cameraStatus.className = 'camera-status connecting';
  cameraFrame.hidden = false;
  cameraImage.hidden = false;
  cameraStart.disabled = true;
  cameraStop.disabled = false;
  cameraImage.src = streamUrl.href;
  cameraConnectTimer = setTimeout(() => {
    if (cameraStatus.classList.contains('connecting')) {
      stopCamera('Hết thời gian chờ');
      cameraHelp.textContent = 'Chưa nhận được hình ảnh. Kiểm tra camera, URL /stream, mạng LAN và thử lại.';
    }
  }, 10000);
});

cameraImage.addEventListener('load', () => {
  if (!cameraImage.hasAttribute('src')) return;
  clearTimeout(cameraConnectTimer);
  cameraStatus.textContent = 'Đang phát';
  cameraStatus.className = 'camera-status online';
  cameraStart.disabled = false;
  cameraHelp.textContent = 'Đang hiển thị trực tiếp từ ESP32-CAM. Luồng preview không chạy pose, không publish MQTT và không lưu frame.';
});

cameraImage.addEventListener('error', () => {
  if (!cameraImage.hasAttribute('src')) return;
  stopCamera('Không truy cập được camera');
  cameraHelp.textContent = 'Không tải được stream. Kiểm tra ESP32-CAM đang bật, URL /stream chính xác, cùng mạng LAN và trình duyệt cho phép tải HTTP.';
});

cameraStop.addEventListener('click', () => stopCamera());
cameraInput.addEventListener('input', () => cameraInput.removeAttribute('aria-invalid'));
window.addEventListener('pagehide', () => stopCamera());

pagePrevious.addEventListener('click', () => {
  if (currentPage > 0) { currentPage -= 1; renderEvents(); updateHistoryCaption(); }
});
pageNext.addEventListener('click', () => {
  if ((currentPage + 1) * PAGE_SIZE < historyItems.length) { currentPage += 1; renderEvents(); updateHistoryCaption(); }
});

form.addEventListener('submit', event => {
  event.preventDefault();
  const data = new FormData(form);
  const nextFilters = {
    seat_id: data.get('seat_id').trim(),
    from: data.get('from'),
    to: data.get('to'),
  };
  try {
    if (nextFilters.from && nextFilters.to && DashboardUtils.utcParam(nextFilters.from) >= DashboardUtils.utcParam(nextFilters.to)) {
      setText('#history-caption', 'Khoảng thời gian không hợp lệ: “Từ” phải trước “Đến”.'); return;
    }
  } catch {
    setText('#history-caption', 'Thời gian bộ lọc không hợp lệ.'); return;
  }
  activeFilters = nextFilters;
  currentPage = 0;
  lastHistorySnapshot = '';
  refresh();
});

form.addEventListener('reset', () => {
  activeFilters = {};
  currentPage = 0;
  lastHistorySnapshot = '';
  setTimeout(refresh, 0);
});

document.addEventListener('visibilitychange', () => {
  if (!document.hidden) refresh();
});

refresh();
setInterval(refresh, 2000);
setInterval(() => updateFreshness(Date.now()), 1000);
