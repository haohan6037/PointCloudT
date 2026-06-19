const API = process.env.EXPO_PUBLIC_API_URL || 'https://mygardenos-mobile-backend-production.up.railway.app';
let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
  const res = await fetch(`${API}${path}`, { headers, ...options });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

export type User = { id:number; email:string; username:string; gender:string; address:string; avatar_url?:string; is_active:boolean };
export type Family = { id:number; code:string; name:string; address:string; members:{id:number; role:string; user:User}[] };
export type Device = { id:number; serial:string; name:string; model:string; status:string; battery_percent:number; owner_id?:number; family_id?:number; last_seen_at?:string; schedule_start_time?:string; schedule_end_time?:string };
export type BluetoothDevice = { peripheral_id:string; serial:string; name:string; model:string; rssi:number; is_bound:boolean; status:string };
export type Settings = { language:string; region:string; device_notifications:boolean; system_notifications:boolean };
export type Article = { slug:string; title:string; category:string; content:string };
export type About = { product:string; version:string; update_status:string; privacy_policy:string; user_agreement:string };

export const api = {
  profile: () => request<User>('/profile'),
  updateProfile: (body: Partial<User> & { password?: string }) => request<User>('/profile', { method:'PATCH', body: JSON.stringify(body) }),
  families: () => request<Family[]>('/families'),
  createFamily: (name: string = 'happy family', address: string = '') => request<Family>('/families', { method:'POST', body: JSON.stringify({ name, address }) }),
  joinFamily: (code: string) => request<Family>('/families/join', { method:'POST', body: JSON.stringify({ code }) }),
  leaveFamily: (id: number) => request<{status:string}>(`/families/${id}/leave`, { method:'POST' }),
  updateFamily: (id:number, body: Partial<Family>) => request<Family>(`/families/${id}`, { method:'PATCH', body: JSON.stringify(body) }),
  dissolveFamily: (id:number) => request<{status:string}>(`/families/${id}`, { method:'DELETE' }),
  devices: () => request<Device[]>('/devices'),
  searchDevices: () => request<Device[]>('/devices/search'),
  bindDevice: (serial:string, family_id?:number) => request<Device>('/devices/bind', { method:'POST', body: JSON.stringify({ serial, family_id }) }),
  scanBluetoothDevices: () => request<BluetoothDevice[]>('/devices/bluetooth/scan'),
  pairBluetoothDevice: (body: { serial:string; peripheral_id?:string; name?:string; model?:string; family_id?:number }) => request<Device>('/devices/bluetooth/pair', { method:'POST', body: JSON.stringify(body) }),
  deviceStatus: (id:number) => request<Device>(`/devices/${id}/status`),
  updateDeviceStatus: (id:number, body: { status?:string; battery_percent?:number }) => request<Device>(`/devices/${id}/status`, { method:'PATCH', body: JSON.stringify(body) }),
  updateDeviceSchedule: (id:number, body: { schedule_start_time:string; schedule_end_time:string }) => request<Device>(`/devices/${id}/schedule`, { method:'PATCH', body: JSON.stringify(body) }),
  notifications: (kind:'device'|'system', read?: boolean) => request<unknown[]>(`/notifications?kind=${kind}${read === undefined ? '' : `&read=${read}`}`),
  settings: () => request<Settings>('/settings'),
  updateSettings: (body: Partial<Settings>) => request<Settings>('/settings', { method:'PATCH', body: JSON.stringify(body) }),
  articles: () => request<Article[]>('/help/articles'),
  article: (slug:string) => request<Article>(`/help/articles/${slug}`),
  about: () => request<About>('/about'),
};
