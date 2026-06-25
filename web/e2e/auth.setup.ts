import { test as setup } from "@playwright/test";
import { signup, expectAuthed } from "./helpers";

// Runs once before the feature specs. Creates a SEPARATE signed-in user per browser
// project and saves each as its own storageState. Separate users matter because all
// browser projects share one backend DB — a shared user would let one browser's writes
// (e.g. "known" marks) leak into another browser's initial-state assertions.
export const BROWSERS = ["chromium", "firefox", "webkit"] as const;
export const storageStateFor = (browser: string) => `e2e/.auth/${browser}.json`;

setup("create authenticated users", async ({ page }) => {
  for (const browser of BROWSERS) {
    // signup() does goto("/") first; a cleared localStorage means it lands on the
    // login form each pass even though we reuse one context.
    await signup(page, {
      email: `e2e-${browser}@test.com`,
      password: "e2e-password",
      displayName: `E2E ${browser}`,
      invite: "e2e-invite",
    });
    await expectAuthed(page);
    await page.context().storageState({ path: storageStateFor(browser) });
    await page.evaluate(() => localStorage.clear()); // next pass starts logged out
  }
});
