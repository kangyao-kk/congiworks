import { api } from './client';

export async function fetchUserProfile() {
  return api.get('/user/profile');
}
