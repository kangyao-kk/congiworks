import { api } from './client';

export async function fetchActivities(agentId) {
  return api.get(`/agents/${agentId}/activities`);
}

export async function addActivity(agentId, activity) {
  return api.post(`/agents/${agentId}/activities`, activity);
}
