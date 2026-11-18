(function exposeDashboardUtils(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.DashboardUtils = api;
}(globalThis, () => {
  function eventFreshness(timestamp, nowMs, staleAfterSeconds = 10) {
    const parsed = Date.parse(timestamp);
    if (!Number.isFinite(parsed)) return {state: 'invalid', ageSeconds: null};
    const ageSeconds = (nowMs - parsed) / 1000;
    if (ageSeconds < 0) return {state: 'future', ageSeconds};
    return {state: ageSeconds <= staleAfterSeconds ? 'fresh' : 'stale', ageSeconds};
  }

  function summarizeFreshness(items, nowMs, staleAfterSeconds = 10) {
    const states = items.map(item => eventFreshness(item.ts, nowMs, staleAfterSeconds).state);
    return {
      total: items.length,
      fresh: states.filter(state => state === 'fresh').length,
      stale: states.filter(state => state === 'stale').length,
      future: states.filter(state => state === 'future').length,
      invalid: states.filter(state => state === 'invalid').length,
    };
  }

  function utcParam(value, timeZone = 'Asia/Ho_Chi_Minh') {
    if (!value) return '';
    const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value);
    if (!match) throw new RangeError('Thời gian bộ lọc không hợp lệ');
    const target = match.slice(1).map(Number);
    const nominal = Date.UTC(target[0], target[1] - 1, target[2], target[3], target[4]);
    const nominalDate = new Date(nominal);
    if (nominalDate.getUTCFullYear() !== target[0] || nominalDate.getUTCMonth() !== target[1] - 1 ||
        nominalDate.getUTCDate() !== target[2] || nominalDate.getUTCHours() !== target[3] ||
        nominalDate.getUTCMinutes() !== target[4]) throw new RangeError('Thời gian bộ lọc không hợp lệ');

    const formatter = new Intl.DateTimeFormat('en-CA', {
      timeZone, year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23',
    });
    let candidate = nominal;
    for (let attempt = 0; attempt < 3; attempt += 1) {
      const parts = Object.fromEntries(formatter.formatToParts(new Date(candidate))
        .filter(part => part.type !== 'literal').map(part => [part.type, Number(part.value)]));
      const displayedAsUtc = Date.UTC(parts.year, parts.month - 1, parts.day, parts.hour, parts.minute, parts.second);
      candidate -= displayedAsUtc - nominal;
    }
    const verified = Object.fromEntries(formatter.formatToParts(new Date(candidate))
      .filter(part => part.type !== 'literal').map(part => [part.type, Number(part.value)]));
    if (verified.year !== target[0] || verified.month !== target[1] || verified.day !== target[2] ||
        verified.hour !== target[3] || verified.minute !== target[4]) {
      throw new RangeError('Thời gian không tồn tại trong múi giờ đã chọn');
    }
    return new Date(candidate).toISOString().replace(/\.\d{3}Z$/, 'Z');
  }

  function compareSeatIds(left, right) {
    return String(left).localeCompare(String(right), 'en', {numeric: true, sensitivity: 'base'});
  }

  function formatAngle(value) {
    if (value == null || !Number.isFinite(Number(value))) return 'Chưa có góc thân';
    return `${Number(value).toFixed(1)}°`;
  }

  function applyEndpointResponse(snapshot, response, receivedAt) {
    if (response.status === 'fulfilled') {
      return {data: response.value, receivedAt, error: ''};
    }
    const error = response.reason || {};
    return {
      data: snapshot.data,
      receivedAt: snapshot.receivedAt,
      error: error.status ? `HTTP ${error.status}` : 'lỗi mạng',
    };
  }

  function hasHttpResponse(responses) {
    return responses.some(response => response.status === 'fulfilled' || Boolean(response.reason?.status));
  }

  function hasAvailableEndpoint(responses) {
    return responses.some(response => response.status === 'fulfilled' ||
      (Number.isInteger(response.reason?.status) && response.reason.status < 500));
  }

  return {
    eventFreshness, summarizeFreshness, utcParam, compareSeatIds, formatAngle,
    applyEndpointResponse, hasHttpResponse, hasAvailableEndpoint,
  };
}));
