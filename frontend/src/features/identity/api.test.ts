import { afterEach, describe, expect, it, vi } from "vitest";
import { authAction, currentAccount } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("same-origin authentication transport", () => {
  it("bootstraps CSRF before each mutation and includes cookies without storing credentials", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ csrf_token: "masked-value" })))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);
    await authAction("logout");
    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/v1/auth/csrf", { credentials: "same-origin", cache: "no-store" });
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/v1/auth/logout", expect.objectContaining({
      method: "POST", credentials: "same-origin", cache: "no-store",
      headers: { "Content-Type": "application/json", "X-CSRFToken": "masked-value" },
    }));
  });

  it("treats an expired or anonymous session as signed out", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 403 })));
    expect(await currentAccount()).toBeNull();
  });

  it("shows server validation errors without exposing raw responses", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ csrf_token: "masked-value" })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: ["This reset link is invalid or has expired."] }), { status: 400 })));
    await expect(authAction("password/reset")).rejects.toThrow("This reset link is invalid or has expired.");
  });
});
