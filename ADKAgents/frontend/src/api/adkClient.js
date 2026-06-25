const APP_NAME = 'bank_agent';

export function generateId() {
  return Math.random().toString(36).substring(2, 11);
}

export async function createSession(userId) {
  const res = await fetch(`/apps/${APP_NAME}/users/${userId}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  });
  if (!res.ok) throw new Error(`Session error: ${res.status} ${await res.text()}`);
  return res.json();
}

function extractErrorMessage(event) {
  // ADK agent-level errors: {errorCode, errorMessage}
  if (event.errorCode && event.errorMessage) {
    const raw = String(event.errorMessage);
    // Pull HTTP status + description from the message
    const match = raw.match(/^(\d{3})\s+[\w_]+\.\s*(.*)/s);
    if (match) {
      // Return a clean version without the nested Python dict
      const detail = match[2].replace(/\{.*\}/s, '').trim();
      return detail || `Server error ${match[1]}`;
    }
    return raw.split('\n')[0].substring(0, 120);
  }
  // Final stream error: {error: "503 UNAVAILABLE ..."}
  if (event.error) {
    const raw = String(event.error);
    if (raw.includes('503') || raw.includes('UNAVAILABLE')) {
      return 'The AI model is temporarily overloaded. Please try again in a few seconds.';
    }
    if (raw.includes('429') || raw.includes('RESOURCE_EXHAUSTED')) {
      return 'API quota exceeded. Please try again shortly.';
    }
    if (raw.includes('404') || raw.includes('NOT_FOUND')) {
      return 'Model not available. Please check your configuration.';
    }
    return raw.split('\n')[0].substring(0, 120);
  }
  return null;
}

export async function* streamMessage(userId, sessionId, text) {
  const res = await fetch('/run_sse', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      appName: APP_NAME,
      userId,
      sessionId,
      newMessage: {
        role: 'user',
        parts: [{ text }],
      },
    }),
  });

  if (!res.ok) throw new Error(`Stream error: ${res.status} ${await res.text()}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const raw = line.slice(6).trim();
      if (!raw || raw === '[DONE]') continue;
      try {
        const event = JSON.parse(raw);
        const errMsg = extractErrorMessage(event);
        if (errMsg) throw new Error(errMsg);
        yield event;
      } catch (err) {
        if (err instanceof SyntaxError) continue;
        throw err;
      }
    }
  }
}
