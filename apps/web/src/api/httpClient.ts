const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

function resolveApiBaseUrl(): string {
  const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL;
  if (!configuredBaseUrl) {
    return DEFAULT_API_BASE_URL;
  }

  return configuredBaseUrl.replace(/\/$/, "");
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${resolveApiBaseUrl()}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`API ${response.status}: ${errorBody || response.statusText}`);
  }

  return (await response.json()) as T;
}
