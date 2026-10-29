/** Session-authenticated JSON requests shared by all feature clients. */
export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

function csrfToken(): string {
  const cookie = document.cookie.split(";").map((value) => value.trim())
    .find((value) => value.startsWith("csrftoken="));
  return cookie ? decodeURIComponent(cookie.slice("csrftoken=".length)) : "";
}

function validationMessage(value: unknown): string {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(validationMessage).filter(Boolean).join(" ");
  if (value && typeof value === "object") {
    return Object.entries(value).map(([key, item]) => {
      const message = validationMessage(item);
      return key === "detail" || key === "nonFieldErrors" ? message : `${key}: ${message}`;
    }).join(" ");
  }
  return "";
}

export async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.body != null && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(options.method ?? "GET")) {
    headers.set("X-CSRFToken", csrfToken());
  }
  const response = await fetch(url, { ...options, headers, credentials: "same-origin" });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    if (response.status === 401) message = "Please log in to continue";
    else if (response.status === 403) message = "You do not have permission to perform this action";
    else if (response.status === 404) message = "Resource not found";
    else if (response.status === 429) message = "Too many requests — please try again shortly";
    else if (response.status >= 500) message = "Server error — please try again later";
    else {
      // DRF validation messages help users correct their input. Never log raw
      // response bodies, which may contain personal data or server diagnostics.
      try { message = validationMessage(await response.json()) || message; } catch { /* Non-JSON error. */ }
    }
    throw new ApiError(message, response.status);
  }
  if (response.status === 204 || options.method === "HEAD") return undefined as T;
  if (!response.headers.get("Content-Type")?.includes("json")) {
    throw new ApiError("Unexpected server response — please reload and try again", response.status);
  }
  return response.json() as Promise<T>;
}
