import { Page, expect } from "@playwright/test";

// Shared Login-form drivers. The form's <label>s aren't htmlFor-associated with their
// inputs (see web/src/screens/Login.tsx), so we locate each input via its wrapping
// `.field` (which holds the label text). The submit button is the only `.btn.wide`.

export type Creds = { email: string; password: string; displayName: string; invite: string };

const field = (page: Page, label: string) =>
  page.locator(".field", { hasText: label }).locator("input");
const submit = (page: Page) => page.locator("button.btn.wide");

export async function signup(page: Page, c: Creds) {
  await page.goto("/");
  await page.getByRole("button", { name: "Sign up" }).click(); // toggle login → signup
  await field(page, "Display name").fill(c.displayName);
  await field(page, "Email").fill(c.email);
  await field(page, "Password").fill(c.password);
  await field(page, "Invite code").fill(c.invite);
  await submit(page).click();
}

export async function login(page: Page, email: string, password: string) {
  await page.goto("/");
  await field(page, "Email").fill(email);
  await field(page, "Password").fill(password);
  await submit(page).click();
}

// Authenticated ⇒ the app shell renders (Log out lives in the topbar).
export const expectAuthed = (page: Page) =>
  expect(page.getByRole("button", { name: "Log out" })).toBeVisible();

// Logged out ⇒ the Login form is back (Email field present).
export const expectLoggedOut = (page: Page) =>
  expect(field(page, "Email")).toBeVisible();
