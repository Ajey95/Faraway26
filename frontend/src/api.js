const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

export async function createAudit(payload) {
  const response = await fetch(`${API_BASE}/audit`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function getAudit(id) {
  const response = await fetch(`${API_BASE}/audit/${id}`);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export function reportUrl(id) { return `${API_BASE}/audit/${id}/report`; }
export function streamUrl(id) { return `${API_BASE}/audit/${id}/stream`; }
