import { test, expect } from "@playwright/test";

// Reading comprehension is graded deterministically server-side (no AI), so we can
// drive the whole flow: open a reading set, answer every question, submit, see a score.
test("answer a reading set and get a graded result", async ({ page }) => {
  await page.goto("/comprehension");
  await expect(page.getByRole("heading", { name: "Read & Listen" })).toBeVisible();

  // open the first Reading set (reading needs no audio asset)
  await page.locator(".unit", { hasText: "Reading" }).locator(".lesson-node").first().click();
  await page.locator(".options").first().waitFor({ state: "visible" }); // wait for the set to load

  // each question card carries an `.options` group — answer the first option of each
  const questions = page.locator(".card", { has: page.locator(".options") });
  const n = await questions.count();
  expect(n).toBeGreaterThan(0);
  for (let i = 0; i < n; i++) {
    await questions.nth(i).locator("button.option").first().click();
  }

  await page.getByRole("button", { name: /^Submit/ }).click();

  // graded results: a pass/fail heading + an "X / Y correct" line
  await expect(page.getByRole("heading", { name: /Passed|Keep practicing/ })).toBeVisible();
  await expect(page.getByText(/\d+ \/ \d+ correct/)).toBeVisible();
});
