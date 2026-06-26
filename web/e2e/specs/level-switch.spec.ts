import { test, expect } from "@playwright/test";

// The level switcher (topbar) drives the skill screens. With a1 + a2 both seeded,
// switching to A2 must repoint the learn path. Authed via the project storageState.
test("switching level repoints the learn path from A1 to A2", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Your path · A1/ })).toBeVisible();

  await page.getByRole("combobox", { name: "Level" }).selectOption("a2");

  await expect(page.getByRole("heading", { name: /Your path · A2/ })).toBeVisible();
});
