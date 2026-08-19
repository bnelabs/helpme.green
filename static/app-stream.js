export function createStreamRequest({headers, onAuthRequired}) {
  return async function streamRequest(url, options, onDelta) {
    const response = await fetch(url, Object.assign({}, options, {headers: headers()}));
    if (response.status === 401) {
      if (typeof onAuthRequired === "function") onAuthRequired();
      const error = new Error("auth_required");
      error.code = "auth_required";
      error.status = response.status;
      throw error;
    }
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      const error = new Error(body.error || ("Request failed (" + response.status + ")"));
      error.code = body.error || "request_failed";
      error.status = response.status;
      throw error;
    }
    if (!response.body) throw Object.assign(new Error("stream_unavailable"), {code: "stream_unavailable"});
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let complete = null;
    const dispatch = (rawEvent) => {
      let eventName = "message";
      const dataLines = [];
      rawEvent.split("\n").forEach((line) => {
        if (line.startsWith("event:")) eventName = line.slice(6).trim();
        if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
      });
      if (!dataLines.length) return;
      const payload = JSON.parse(dataLines.join("\n"));
      if (eventName === "delta" && payload.text) onDelta(payload.text);
      if (eventName === "complete") complete = payload;
      if (eventName === "error") {
        const error = new Error(payload.error || "stream_failed");
        error.code = payload.error || "stream_failed";
        throw error;
      }
    };
    while (true) {
      const result = await reader.read();
      buffer += decoder.decode(result.value || new Uint8Array(), {stream: !result.done});
      buffer = buffer.replace(/\r\n/g, "\n");
      const events = buffer.split("\n\n");
      buffer = events.pop() || "";
      events.forEach(dispatch);
      if (result.done) break;
    }
    if (buffer.trim()) dispatch(buffer);
    if (!complete) throw Object.assign(new Error("stream_incomplete"), {code: "stream_incomplete"});
    return complete;
  };
}
