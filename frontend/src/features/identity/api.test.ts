import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, authAction, currentAccount } from "./api";

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
      .mockResolvedValueOnce(new Response(JSON.stringify({ code: "validation_error", detail: "Check the highlighted fields.",
        errors: [{ path: "", code: "invalid_reset", message: "This reset link is invalid or has expired." }] }), { status: 400 })));
    await expect(authAction("password/reset")).rejects.toThrow("This reset link is invalid or has expired.");
  });

  it("retains field errors and a matching server request reference", async () => {
    const requestId = "3fbbcd4f-b207-4712-bcbd-1b55da617db6";
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ csrf_token: "masked-value" })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ code: "validation_error", detail: "Check the highlighted fields.",
        errors: [{ path: "/email", code: "required", message: "This field is required." }], request_id: requestId }),
      { status: 400, headers: { "X-Request-ID": requestId } })));
    await expect(authAction("login")).rejects.toMatchObject({
      name: "ApiError", code: "validation_error", requestId,
      fields: [{ path: "/email", code: "required", message: "This field is required." }],
    });
  });

  it.each(["<html>unexpected proxy response</html>", "null", JSON.stringify({ detail: "unexpected internal response" })])(
    "uses a safe fallback for a response outside the API contract", async (body) => {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ csrf_token: "masked-value" })))
        .mockResolvedValueOnce(new Response(body, { status: 502 })));
      const failure = await authAction("login").catch((error: unknown) => error);
      expect(failure).toBeInstanceOf(ApiError);
      expect(failure).toMatchObject({ code: "transport_error", fields: [],
        message: "We couldn’t complete that request. Check your details and try again." });
      expect(fetch).toHaveBeenCalledTimes(2);
    },
  );
});
