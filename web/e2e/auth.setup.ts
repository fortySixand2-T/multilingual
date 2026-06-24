import { test as setup } from "@playwright/test";
import { signup, expectAuthed } from "./helpers";

// Runs once before the feature specs (the `setup` project). Signs up a known user
// through the real UI and saves the resulting auth (JWT in localStorage) as a
// storageState the chromium project reuses — so feature specs start already signed in.
const authFile = "e2e/.auth/user.json";

setup("create authenticated user", async ({ page }) => {
  await signup(page, {
    email: "e2e@test.com",
    password: "e2e-password",
    displayName: "E2E User",
    invite: "e2e-invite",
  });
  await expectAuthed(page);
  await page.context().storageState({ path: authFile });
});
