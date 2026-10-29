export type Account = {
  id: string;
  email: string;
  display_name: string;
  timezone: string;
  workspaces: { id: string; name: string; role: string }[];
};

export type FieldError = { path: string; code: string; message: string };

export class ApiError extends Error {
  constructor(message: string, public code: string, public fields: FieldError[], public requestId?: string) {
    super(message);
    this.name = "ApiError";
  }
}

const errorCodes = new Set([
  "validation_error", "parse_error", "invalid_credentials", "authentication_required",
  "permission_denied", "csrf_failed", "not_found", "method_not_allowed", "not_acceptable",
  "unsupported_media_type", "rate_limited", "internal_error", "service_unavailable",
]);
const requestIdPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

async function decode(response: Response) {
  const data = response.status === 204 ? {} : await response.json().catch(() => ({}));
  if (!response.ok) {
    if (data && typeof data === "object" && errorCodes.has(data.code) &&
      typeof data.detail === "string" && Array.isArray(data.errors)) {
      const fields: FieldError[] = data.errors.filter((field: FieldError) => field &&
        typeof field.path === "string" && typeof field.code === "string" &&
        typeof field.message === "string").slice(0, 100);
      const message = fields.find((field) => field.path === "")?.message ?? data.detail;
      const requestId = typeof data.request_id === "string" && requestIdPattern.test(data.request_id) &&
        response.headers.get("X-Request-ID") === data.request_id ? data.request_id : undefined;
      throw new ApiError(message, data.code, fields, requestId);
    }
    const message = response.status === 403 ? "Your session or security token has expired. Sign in or try again." :
      response.status === 429 ? "Too many attempts. Please try again later." :
      "We couldn’t complete that request. Check your details and try again.";
    throw new ApiError(message, "transport_error", []);
  }
  return data;
}

export async function currentAccount(): Promise<Account | null> {
  const response = await fetch("/api/v1/auth/me", { credentials: "same-origin", cache: "no-store" });
  if (response.status === 403 || response.status === 401) return null;
  return (await decode(response)).user;
}

export async function authAction(path: string, values: Record<string, string> = {}) {
  const csrf = await decode(await fetch("/api/v1/auth/csrf", {
    credentials: "same-origin", cache: "no-store",
  }));
  return decode(await fetch(`/api/v1/auth/${path}`, {
    method: "POST", credentials: "same-origin", cache: "no-store",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrf.csrf_token },
    body: JSON.stringify(values),
  }));
}
