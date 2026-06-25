import { test, expect } from "@playwright/test";

// The SRS review flow: a freshly-added card is due now, so we can reveal it and rate it.
test("reveal and rate a due review card", async ({ page }) => {
  // seed a due card via the deck's "Add to review"
  await page.goto("/vocab/a1/all");
  await Promise.all([
    page.waitForResponse((r) => r.url().includes("/srs/add") && r.request().method() === "POST"),
    page.getByRole("button", { name: /Add to review/ }).click(),
  ]);

  await page.goto("/review");
  await page.getByRole("button", { name: "Show answer" }).click();

  // rating buttons appear; "Good" reschedules and advances
  await Promise.all([
    page.waitForResponse((r) => r.url().includes("/srs/review") && r.request().method() === "POST"),
    page.getByRole("button", { name: "Good" }).click(),
  ]);

  // after rating: either the next card's "Show answer" or the caught-up screen
  await expect(
    page.getByRole("button", { name: "Show answer" }).or(page.getByText("All caught up")),
  ).toBeVisible();
});
