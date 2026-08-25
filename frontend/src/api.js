const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

export async function evaluateCompany(companyName, { refresh = false } = {}) {
  const url = new URL("/api/evaluate", API_BASE);
  url.searchParams.set("company", companyName);
  if (refresh) url.searchParams.set("refresh", "true");

  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(body.detail || `요청 실패 (${res.status})`, res.status);
  }
  return res.json();
}
