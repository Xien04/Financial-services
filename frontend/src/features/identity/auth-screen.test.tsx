import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AuthScreen from "./auth-screen";
import { ApiError, authAction, currentAccount } from "./api";

vi.mock("./api", async (importOriginal) => ({
  ...await importOriginal<typeof import("./api")>(), currentAccount: vi.fn(), authAction: vi.fn(),
}));
const account = { id: "user-id", email: "owner@example.test", display_name: "Owner", timezone: "Asia/Manila",
  workspaces: [{ id: "workspace-id", name: "Personal", role: "owner" }] };

describe("authentication workflows", () => {
  beforeEach(() => { vi.mocked(currentAccount).mockResolvedValue(null); });
  afterEach(() => { window.history.replaceState(null, "", "/"); vi.useRealTimers(); });

  async function fillLogin() {
    fireEvent.change(await screen.findByLabelText("Email address"), { target: { value: account.email } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "submitted-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
  }

  it("signs in, shows current workspace membership, and signs out", async () => {
    vi.mocked(authAction).mockResolvedValue({ user: account });
    render(<AuthScreen />);
    await fillLogin();
    expect(await screen.findByRole("heading", { name: "Welcome, Owner." })).toBeVisible();
    expect(screen.getByText("Personal · owner")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));
    expect(await screen.findByRole("button", { name: "Sign in" })).toBeVisible();
    expect(authAction).toHaveBeenCalledWith("logout");
  });

  it("preserves input, focuses the error, and permits retry after a rejected login", async () => {
    vi.mocked(authAction).mockRejectedValue(new Error("Email or password is incorrect."));
    render(<AuthScreen />);
    await fillLogin();
    expect(await screen.findByRole("alert")).toHaveFocus();
    expect(screen.getByLabelText("Email address")).toHaveValue(account.email);
    expect(screen.getByRole("button", { name: "Sign in" })).toBeEnabled();
  });

  it("marks declared fields and displays the correlated support reference", async () => {
    const requestId = "3fbbcd4f-b207-4712-bcbd-1b55da617db6";
    vi.mocked(authAction).mockRejectedValue(new ApiError("Check the highlighted fields.",
      "validation_error", [{ path: "/email", code: "invalid", message: "Enter a valid value." }], requestId));
    render(<AuthScreen />);
    await fillLogin();
    expect(await screen.findByRole("alert")).toHaveTextContent(requestId);
    expect(screen.getByLabelText(/Email address/)).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText(/Email address/)).toHaveAccessibleDescription("Enter a valid value.");
  });

  it("disables repeated submissions while login is pending", async () => {
    let finish: (value: object) => void = () => {};
    vi.mocked(authAction).mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
    render(<AuthScreen />);
    await fillLogin();
    expect(screen.getByRole("button", { name: "Please wait…" })).toBeDisabled();
    await act(async () => { finish({ user: account }); });
  });

  it("shows a generic recovery response", async () => {
    vi.mocked(authAction).mockResolvedValue({ detail: "If an active account matches, a password reset email will be sent." });
    render(<AuthScreen mode="recover" />);
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "missing@example.test" } });
    fireEvent.click(screen.getByRole("button", { name: "Send reset link" }));
    expect(await screen.findByRole("status")).toHaveTextContent("If an active account matches");
    expect(authAction).toHaveBeenCalledWith("password/recover", { email: "missing@example.test" });
  });

  it("removes reset credentials from browser history and submits them only in the reset body", async () => {
    window.history.replaceState(null, "", "/reset-password#uid=encoded-user&token=reset-value");
    vi.mocked(authAction).mockResolvedValue({ detail: "Password reset. Sign in with your new password." });
    render(<AuthScreen mode="reset" />);
    expect(window.location.hash).toBe("");
    fireEvent.change(await screen.findByLabelText("New password"), { target: { value: "new-password-example" } });
    fireEvent.change(screen.getByLabelText("Confirm new password"), { target: { value: "new-password-example" } });
    fireEvent.click(screen.getByRole("button", { name: "Reset password" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Password reset");
    expect(authAction).toHaveBeenCalledWith("password/reset", expect.objectContaining({ uid: "encoded-user", token: "reset-value" }));
    expect(vi.mocked(authAction).mock.calls.at(-1)?.[1]).not.toHaveProperty("confirm_password");
    expect(screen.queryByLabelText("New password")).not.toBeInTheDocument();
  });

  it("offers a new reset link when reset credentials are missing", () => {
    render(<AuthScreen mode="reset" />);
    expect(screen.queryByRole("button", { name: "Reset password" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Request a new reset link" })).toBeVisible();
  });

  it("validates password confirmation before sending a change", async () => {
    vi.mocked(currentAccount).mockResolvedValue(account);
    render(<AuthScreen />);
    fireEvent.change(await screen.findByLabelText("Current password"), { target: { value: "current-example" } });
    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "new-password-example" } });
    fireEvent.change(screen.getByLabelText("Confirm new password"), { target: { value: "different-password-example" } });
    fireEvent.click(screen.getByRole("button", { name: "Change password and sign out" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("do not match");
    expect(authAction).not.toHaveBeenCalled();
  });

  it("shows an actionable error when the initial connection fails", async () => {
    vi.mocked(currentAccount).mockRejectedValue(new Error("offline"));
    render(<AuthScreen />);
    expect(await screen.findByRole("alert")).toHaveTextContent("refresh to try again");
  });

  it("extends activity only after user input and returns to sign-in when the session expires", async () => {
    vi.mocked(currentAccount).mockResolvedValue(account);
    vi.mocked(authAction).mockRejectedValue(new Error("expired"));
    render(<AuthScreen />);
    await screen.findByRole("heading", { name: "Welcome, Owner." });
    const later = Date.now() + 61_000;
    vi.spyOn(Date, "now").mockReturnValue(later);
    expect(authAction).not.toHaveBeenCalled();
    fireEvent.keyDown(window, { key: "Tab" });
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("session has expired"));
    expect(screen.getByRole("button", { name: "Sign in" })).toBeVisible();
  });
});
