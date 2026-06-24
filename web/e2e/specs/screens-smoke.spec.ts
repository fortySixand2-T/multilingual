import { test, expect } from "@playwright/test";

// Smoke coverage for the remaining screens. These either depend on AI (writing grade,
// drill generation) or the mic (speaking) — none available in CI — so we assert the
// screen loads and renders its controls, without invoking the unavailable backend.

test("writing: task list opens a task editor", async ({ page }) => {
  await page.goto("/writing");
  await expect(page.getByRole("heading", { name: "Writing" })).toBeVisible();
  await page.locator(".lesson-node").first().click();
  // the editor renders (prompt + the response textarea); we don't submit (AI grader)
  await expect(page.getByPlaceholder("Écrivez votre réponse ici…")).toBeVisible();
});

test("drill: the generator screen renders", async ({ page }) => {
  await page.goto("/drill");
  await expect(page.getByRole("heading", { name: "Practice drill" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Give me a drill" })).toBeVisible();
});

test("speaking: the recorder screen renders", async ({ page }) => {
  await page.goto("/speaking");
  await expect(page.getByRole("heading", { name: "Speaking" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Record/ })).toBeVisible();
});

test("group board renders", async ({ page }) => {
  await page.goto("/board");
  await expect(page.getByRole("heading", { name: "Group board" })).toBeVisible();
  // the board card is present whether or not anyone has earned XP yet
  await expect(page.locator(".card").first()).toBeVisible();
});
