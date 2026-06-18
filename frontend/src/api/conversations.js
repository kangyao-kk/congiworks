import { api } from './client';

export async function clearConversations(agentId) {
  return api.delete(`/agents/${agentId}/conversations`);
}

export async function fetchConversations(agentId) {
  try {
    const msgs = await api.get(`/agents/${agentId}/conversations`);
    return msgs.map((m) => ({
      ...m,
      thinking: m.thinking || undefined,
    }));
  } catch {
    return [];
  }
}

/**
 * 发送消息，通过 SSE 流式接收回复。
 *
 * @param {string} agentId
 * @param {string} content
 * @param {(token: string) => void} onToken  — 每收到一个 token 时回调
 * @returns {Promise<{userMsg: object, aiMsg: object}>}
 */
export async function sendMessage(agentId, content, onToken) {
  const res = await api.post(
    `/agents/${agentId}/conversations`,
    { content },
    { raw: true }
  );

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `HTTP ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let userMsg = null;
  let aiMsg = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const payload = line.slice(6).trim();
      if (payload === '[DONE]') continue;

      try {
        const event = JSON.parse(payload);
        switch (event.type) {
          case 'user_message':
            userMsg = event.data;
            break;
          case 'token':
            if (onToken) onToken(event.data);
            break;
          case 'assistant_message':
            aiMsg = event.data;
            break;
          case 'error':
            throw new Error(event.data);
        }
      } catch (e) {
        if (e.message && !e.message.startsWith('Unexpected')) throw e;
      }
    }
  }

  if (!userMsg || !aiMsg) {
    throw new Error('未收到完整的对话回复');
  }

  return { userMsg, aiMsg };
}
