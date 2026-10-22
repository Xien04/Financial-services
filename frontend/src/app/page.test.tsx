import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import HomePage from "./page";
import { currentAccount } from "../features/identity/api";

vi.mock("../features/identity/api", () => ({ currentAccount: vi.fn(), authAction: vi.fn() }));

describe("the authentication entry page", () => {
  beforeEach(() => vi.mocked(currentAccount).mockResolvedValue(null));

  it("shows accessible sign-in fields after checking the session", async () => {
    render(<HomePage />);
    expect(await screen.findByRole("region", { name: "Sign in to your private workspace." })).toBeVisible();
    expect(screen.getByLabelText("Email address")).toHaveAttribute("autocomplete", "username");
    expect(screen.getByLabelText("Password")).toHaveAttribute("autocomplete", "current-password");
  });

  it("explains operator provisioning and offers password recovery", async () => {
    render(<HomePage />);
    expect(await screen.findByText(/Access is set up by your operator/)).toBeVisible();
    expect(screen.getByRole("link", { name: "Forgot password?" })).toHaveAttribute("href", "/forgot-password");
    expect(screen.queryByRole("link", { name: /register|sign up/i })).not.toBeInTheDocument();
  });

  it("does not present a fabricated balance", async () => {
    const { container } = render(<HomePage />);
    await screen.findByRole("button", { name: "Sign in" });
    expect(container).not.toHaveTextContent(/₱\s*0[.,]00/);
  });
});
