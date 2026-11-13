import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import Credits from "./Credits";

describe("Credits", () => {
  it("credits Wiktionary and Lexique, says they were adapted, and links the licence", () => {
    render(<Credits />);
    expect(screen.getByRole("link", { name: "Wiktionary" })).toHaveAttribute("href", "https://en.wiktionary.org");
    expect(screen.getByRole("link", { name: "Lexique 3" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "CC BY-SA 4.0" })).toHaveAttribute(
      "href",
      "https://creativecommons.org/licenses/by-sa/4.0/",
    );
    expect(screen.getByText(/adapted and shortened/)).toBeInTheDocument();
  });
});
