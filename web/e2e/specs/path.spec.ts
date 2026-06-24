import { test, expect } from "@playwright/test";

// The learn path (home). Authed via the project storageState.
test("the path renders units, lessons, and the XP header", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Your path/ })).toBeVisible();
  // at least one unit with a tappable lesson node
  await expect(page.locator(".unit").first()).toBeVisible();
  await expect(page.locator(".lesson-node").first()).toBeVisible();
  // XP / streak pills come from /progress/me
  await expect(page.getByText(/XP/).first()).toBeVisible();
});
