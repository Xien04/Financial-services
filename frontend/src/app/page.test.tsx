import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import HomePage from "./page";

describe("the foundation welcome page", () => {
  it("gives the welcome section an accessible name", () => {
    render(<HomePage />);

    const welcome = screen.getByRole("region", { name: "A clearer view of your money." });
    expect(within(welcome).getByRole("heading", { level: 1 })).toBeVisible();
  });

  it("explains that account setup and transaction tracking are not available yet", () => {
    render(<HomePage />);

    const notice = screen.getByRole("note");
    expect(within(notice).getByRole("heading", { level: 2 })).toBeVisible();
    expect(notice).toHaveTextContent("Account setup and transaction tracking are coming next.");
  });

  it("does not present a fabricated balance before accounts exist", () => {
    const { container } = render(<HomePage />);

    expect(container).not.toHaveTextContent(/₱\s*0[.,]00/);
  });
});
