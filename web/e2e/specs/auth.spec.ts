import { test } from "@playwright/test";
import { signup, login, expectAuthed, expectLoggedOut } from "../helpers";

// This spec exercises the auth flow itself, so it must start signed OUT — override
// the project's shared storageState with a clean one.
test.use({ storageState: { cookies: [], origins: [] } });

const creds = {
  email: "auth-flow@test.com",
  password: "auth-flow-pw",
  displayName: "Auth Flow",
  invite: "e2e-invite",
};

test("signup → logout → login round-trip", async ({ page }) => {
  await signup(page, creds);
  await expectAuthed(page);

  await page.getByRole("button", { name: "Log out" }).click();
  await expectLoggedOut(page);

  await login(page, creds.email, creds.password);
  await expectAuthed(page);
});
