export type Account = {
  id: string;
  email: string;
  display_name: string;
  timezone: string;
  workspaces: { id: string; name: string; role: string }[];
};

async function decode(response: Response) {
  const data = response.status === 204 ? {} : await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail;
    const message = typeof detail === "string" ? detail : Array.isArray(detail) ? detail.join(" ") :
      response.status === 403 ? "Your session or security token has expired. Sign in or try again." :
      response.status === 429 ? "Too many attempts. Please try again later." :
      "We couldn’t complete that request. Check your details and try again.";
    throw new Error(message);
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
