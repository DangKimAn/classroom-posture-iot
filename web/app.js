const connection = document.querySelector('#connection');
const latestBox = document.querySelector('#seat-map');
const historyBox = document.querySelector('#history');
const form = document.querySelector('#filters');
const seatOptions = document.querySelector('#seat-options');
const labelText = {upright: 'Thẳng', slouching: 'Cúi', leaning: 'Nghiêng', unknown: 'Chưa xác định'};
let activeFilters = {};
let inFlight = false;
let lastLatestSnapshot = '';
let lastHistorySnapshot = '';
let lastSeatOptionsSnapshot = '';

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
  connection.lastElementChild.textContent = online ? 'Backend đang hoạt động' : 'Mất kết nối backend';
  setText('#api-metric', online ? 'Online' : 'Offline');
  setText('#api-caption', online ? 'API phản hồi bình thường' : 'Không nhận được phản hồi từ API');
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
    return await response.json();
  } finally {
    clearTimeout(timeout);
  }
}

function updatePostureCounts(items) {
  const counts = {upright: 0, slouching: 0, leaning: 0, unknown: 0};
  for (const item of items) if (Object.hasOwn(counts, item.label)) counts[item.label] += 1;
  for (const [label, count] of Object.entries(counts)) {
    setText(`#count-${label}`, count);
    const meter = document.querySelector(`#count-${label}`).parentElement.querySelector('[role="meter"]');
    meter.setAttribute('aria-valuemax', Math.max(1, items.length));
    meter.setAttribute('aria-valuenow', count);
    document.querySelector(`#bar-${label}`).style.width = items.length ? `${count / items.length * 100}%` : '0%';
  }
  setText('#seat-count', items.length);
}

function renderSeats(items) {
  latestBox.replaceChildren();
  if (!items.length) {
    latestBox.innerHTML = '<div class="empty-state"><span class="empty-icon">⌁</span><strong>Chưa có sự kiện</strong><p>Vị trí sẽ xuất hiện khi backend nhận được dữ liệu tư thế.</p></div>';
    return;
  }
  for (const event of items) {
    const card = document.createElement('article');
    card.className = `seat-card posture-${event.label}`;
    const icon = document.createElement('span'); icon.className = 'seat-icon'; icon.textContent = 'S';
    const details = document.createElement('div'); details.className = 'seat-details';
    const name = document.createElement('strong'); name.textContent = event.seat_id;
    const state = document.createElement('span'); state.className = 'seat-state'; state.textContent = labelText[event.label] || event.label;
    details.append(name, state);
    const angle = document.createElement('span'); angle.className = 'seat-angle';
    angle.textContent = event.trunk_angle == null ? '—' : `${event.trunk_angle}°`;
    card.append(icon, details, angle);
    const time = document.createElement('span'); time.className = 'seat-time'; time.textContent = formatTime(event.ts);
    time.title = `${new Date(event.ts).toISOString()} UTC`;
    card.append(time);
    latestBox.append(card);
  }
}

function renderEvents(items) {
  historyBox.replaceChildren();
  if (!items.length) {
    historyBox.innerHTML = '<div class="empty-inline">Không có sự kiện phù hợp với bộ lọc.</div>';
    return;
  }
  for (const event of items.slice(0, 8)) {
    const row = document.createElement('article');
    row.className = `event-row posture-${event.label}`;
    const marker = document.createElement('span'); marker.className = 'event-marker';
    marker.textContent = event.label === 'upright' ? '✓' : event.label === 'unknown' ? '?' : '↗';
    const body = document.createElement('div'); body.className = 'event-body';
    const top = document.createElement('div'); top.className = 'event-topline';
    const label = document.createElement('strong'); label.textContent = labelText[event.label] || event.label;
    const seat = document.createElement('span'); seat.className = 'event-seat'; seat.textContent = event.seat_id;
    const timestamp = document.createElement('time'); timestamp.textContent = formatTime(event.ts);
    timestamp.title = `${new Date(event.ts).toISOString()} UTC`;
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

function utcParam(value) {
  if (!value) return '';
  return new Date(`${value}Z`).toISOString().replace(/\.\d{3}Z$/, 'Z');
}

async function refresh() {
  if (inFlight || document.hidden) return;
  inFlight = true;
  try {
    const query = new URLSearchParams();
    if (activeFilters.seat_id) query.set('seat_id', activeFilters.seat_id);
    if (activeFilters.from) query.set('from', utcParam(activeFilters.from));
    if (activeFilters.to) query.set('to', utcParam(activeFilters.to));
    query.set('limit', '100');
    const [latest, history] = await Promise.all([
      getJson('/api/events/latest'),
      getJson(`/api/events?${query}`),
    ]);
    const latestSnapshot = JSON.stringify(latest);
    if (latestSnapshot !== lastLatestSnapshot) {
      renderSeats(latest);
      lastLatestSnapshot = latestSnapshot;
    }
    updatePostureCounts(latest);
    const historySnapshot = JSON.stringify(history);
    if (historySnapshot !== lastHistorySnapshot) {
      renderEvents(history);
      lastHistorySnapshot = historySnapshot;
    }
    const seatOptionsSnapshot = JSON.stringify(latest.map(event => event.seat_id).sort());
    if (seatOptionsSnapshot !== lastSeatOptionsSnapshot) {
      seatOptions.replaceChildren();
      for (const seatId of JSON.parse(seatOptionsSnapshot)) {
        const option = document.createElement('option');
        option.value = seatId;
        seatOptions.append(option);
      }
      lastSeatOptionsSnapshot = seatOptionsSnapshot;
    }
    setText('#event-count', history.length);
    setText('#history-caption', `Hiển thị ${Math.min(history.length, 8)} / ${history.length} sự kiện gần đây`);
    updateConnection(true);
  } catch (error) {
    if (error.status >= 400 && error.status < 500) {
      updateConnection(true);
      setText('#history-caption', 'Bộ lọc không hợp lệ');
    } else {
      updateConnection(false);
      setText('#history-caption', 'Không tải được dữ liệu');
    }
    console.error(error);
  } finally {
    inFlight = false;
  }
}

form.addEventListener('submit', event => {
  event.preventDefault();
  const data = new FormData(form);
  activeFilters = {
    seat_id: data.get('seat_id').trim(),
    from: data.get('from'),
    to: data.get('to'),
  };
  if (activeFilters.from && activeFilters.to && utcParam(activeFilters.from) > utcParam(activeFilters.to)) {
    setText('#history-caption', 'Khoảng thời gian không hợp lệ: “Từ” phải trước “Đến”.');
    return;
  }
  refresh();
});

form.addEventListener('reset', () => {
  activeFilters = {};
  setTimeout(refresh, 0);
});

document.addEventListener('visibilitychange', () => {
  if (!document.hidden) refresh();
});

refresh();
setInterval(refresh, 2000);
