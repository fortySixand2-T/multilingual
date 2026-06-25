import { test } from "@playwright/test";
import { signup, login, expectAuthed, expectLoggedOut } from "../helpers";

// This spec exercises the auth flow itself, so it must start signed OUT — override
// the project's shared storageState with a clean one.
test.use({ storageState: { cookies: [], origins: [] } });

test("signup → logout → login round-trip", async ({ page }, testInfo) => {
  // Unique email per browser project — this spec runs in all of them against one
  // shared backend, so a fixed email would collide on the second browser's signup.
  const creds = {
    email: `auth-flow-${testInfo.project.name}@test.com`,
    password: "auth-flow-pw",
    displayName: "Auth Flow",
    invite: "e2e-invite",
  };
  await signup(page, creds);
  await expectAuthed(page);

  await page.getByRole("button", { name: "Log out" }).click();
  await expectLoggedOut(page);

  await login(page, creds.email, creds.password);
  await expectAuthed(page);
});
