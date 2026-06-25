import { test, expect } from "@playwright/test";

// Authed via the project's per-browser storageState (e2e-<browser>@test.com). These hit
// the real backend, so they prove the persistence round-trips the mocked component tests
// can't see.

test("known counter persists across a reload", async ({ page }) => {
  await page.goto("/vocab/a1/all");
  await expect(page.getByText(/✓ 0 \/ \d+ known/)).toBeVisible();

  await page.getByRole("button", { name: "Show meaning" }).click();
  // "Knew it" persists via POST /content/vocab/known — wait for it before reloading.
  await Promise.all([
    page.waitForResponse(
      (r) => r.url().includes("/content/vocab/known") && r.request().method() === "POST",
    ),
    page.getByRole("button", { name: "Knew it" }).click(),
  ]);
  await expect(page.getByText(/✓ 1 \/ \d+ known/)).toBeVisible();

  await page.reload();
  await expect(page.getByText(/✓ 1 \/ \d+ known/)).toBeVisible();
});

test("a card offers a pronunciation button", async ({ page }) => {
  await page.goto("/vocab/a1/all");
  await expect(page.getByRole("button", { name: "🔊" })).toBeVisible();
});

test("add to review surfaces a due card in the Review queue", async ({ page }) => {
  await page.goto("/vocab/a1/all");
  // Seeds an SRS card via POST /srs/add.
  await Promise.all([
    page.waitForResponse((r) => r.url().includes("/srs/add") && r.request().method() === "POST"),
    page.getByRole("button", { name: /Add to review/ }).click(),
  ]);
  await expect(page.getByRole("button", { name: /In review/ })).toBeVisible();

  // The seeded card is due now → it shows up in the Review queue (proves /srs/add
  // actually entered the schedule, not just flipped a flag).
  await page.goto("/review");
  await expect(page.getByRole("button", { name: "Show answer" })).toBeVisible();
});
