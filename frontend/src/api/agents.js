import { api } from './client';

export async function fetchAgents() {
  return api.get('/agents');
}

export async function fetchAgentById(id) {
  return api.get(`/agents/${id}`);
}

export async function updateAgentStatus(id, status) {
  return api.patch(`/agents/${id}`, { status });
}
