import { test, expect, Page } from "@playwright/test";

// The mock exam is self-reported (record a result per section) — no AI on the record
// or finish path — so the full attempt → CLB report flow is driveable end-to-end.

async function recordAllSections(page: Page) {
  const recordBtns = page.getByRole("button", { name: "Record" });
  expect(await recordBtns.count()).toBeGreaterThan(0);
  // Record the first un-recorded section each pass until none remain. Recording can
  // clear more than one button at once (sections sharing a skill share a recorded
  // flag), so just wait for the count to *decrease* rather than drop by exactly one.
  for (let guard = 0; guard < 8; guard++) {
    const before = await recordBtns.count();
    if (before === 0) break;
    const card = page.locator(".card", { has: page.getByRole("button", { name: "Record" }) }).first();
    const correct = card.getByPlaceholder("correct");
    const points = card.getByPlaceholder("points");
    if (await correct.count()) {
      // comprehension section wants correct / total; anything valid records a band
      await correct.fill("1");
      await card.getByPlaceholder("total").fill("1");
    } else if (await points.count()) {
      await points.fill("15"); // DELF writing/speaking: points /25
    }
    // TEF writing/speaking sections record on the default CLB select — just click Record
    await card.getByRole("button", { name: "Record" }).click();
    await expect.poll(() => recordBtns.count()).toBeLessThan(before);
  }
}

test("start a mock, record every section, finish to a CLB report", async ({ page }) => {
  await page.goto("/exam");
  await expect(page.getByRole("heading", { name: "Mock exam" })).toBeVisible();

  // the cross-level TEF Canada mock
  await page.locator(".unit", { hasText: "TEF Canada — full exam" }).locator(".lesson-node").first().click();
  await expect(page.getByRole("button", { name: /Record every section|Finish & see CLB report/ })).toBeVisible();

  await recordAllSections(page);

  await page.getByRole("button", { name: "Finish & see CLB report" }).click();
  await expect(page.getByRole("heading", { name: "Mock results" })).toBeVisible();
  await expect(page.getByText(/CLB/).first()).toBeVisible();
});

test("start a DELF mock, score each épreuve /25, finish to a pass/fail result", async ({ page }) => {
  await page.goto("/exam");
  await page.locator(".unit", { hasText: "DELF" }).locator(".lesson-node").first().click();
  await expect(page.getByRole("link", { name: /Document 4/ }).first()).toBeVisible();

  await recordAllSections(page);

  await page.getByRole("button", { name: "Finish & see DELF result" }).click();
  await expect(page.getByRole("heading", { name: "Mock results" })).toBeVisible();
  // 1/1 comprehension = 25 each + 15 + 15 → 80/100, a pass
  await expect(page.getByText("80 / 100")).toBeVisible();
  await expect(page.getByText("Pass", { exact: true })).toBeVisible();
});
