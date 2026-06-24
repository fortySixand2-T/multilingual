import { test, expect, Page } from "@playwright/test";

// Drives a lesson to a graded result through the real backend (GET /content/lessons
// + POST /progress/.../result). It's answer-agnostic: most exercise types accept any
// submission and advance, but match_pairs only advances once every pair is matched
// correctly (no wrong-submit path), so that one is brute-forced.

const resultHeading = (page: Page) =>
  page.getByRole("heading", { name: /Lesson complete!|Almost there/ });

async function solveMatchPairs(page: Page) {
  const lefts = page.locator(".exercise .stack").nth(0).locator("button.option");
  const rights = page.locator(".exercise .stack").nth(1).locator("button.option");
  const leftCount = await lefts.count();
  for (let i = 0; i < leftCount; i++) {
    const left = lefts.nth(i);
    if (!(await left.isEnabled())) continue; // already matched
    const rCount = await rights.count();
    for (let j = 0; j < rCount; j++) {
      const right = rights.nth(j);
      if (!(await right.isEnabled())) continue;
      await left.click();
      await right.click();
      if (!(await left.isEnabled())) break; // correct → this left is now locked in
    }
  }
}

async function solveCurrent(page: Page) {
  await page.locator(".exercise").waitFor({ state: "visible" }); // wait for the new exercise to mount
  if (await page.getByText("Match the pairs").isVisible().catch(() => false)) {
    await solveMatchPairs(page); // no Check button — matching all pairs auto-advances
    return;
  }
  const input = page.locator(".exercise input.text-input");
  const tiles = page.locator(".exercise .tiles button.tile");
  if (await input.count()) {
    await input.first().fill("x"); // listen_type / translate — just needs a non-empty value
  } else if (await tiles.count()) {
    await tiles.first().click(); // word_bank — one token is enough to enable Check
  } else {
    await page.locator(".exercise .option").first().click(); // mcq
  }
  await page.getByRole("button", { name: "Check" }).click();
}

test("complete a lesson end-to-end to a graded result", async ({ page }) => {
  await page.goto("/lesson/greetings-01");
  await expect(page.locator(".exercise")).toBeVisible();

  for (let step = 0; step < 12; step++) {
    await solveCurrent(page);
    // The advance button unmounts itself on click (next exercise / result screen), so
    // dispatchEvent — no post-click stability wait that would fail on the detach.
    const advance = page.getByRole("button", { name: /Continue|Finish/ });
    await advance.waitFor({ state: "visible" });
    const last = (await advance.textContent())?.trim() === "Finish";
    await advance.dispatchEvent("click");
    if (last) break;
  }

  await expect(resultHeading(page)).toBeVisible();
  await expect(page.getByText(/You got \d+ \/ \d+ right/)).toBeVisible();

  await page.getByRole("link", { name: "Back to path" }).click();
  await expect(page.getByRole("button", { name: "Log out" })).toBeVisible(); // back in the app shell
});
