// frontend/e2e/helpers/ui.ts
// Small UI helpers shared by the specs. Everything uses accessible locators
// (roles / labels) so the tests survive styling changes.
import { expect, type Locator, type Page } from "@playwright/test";

export type Credentials = { username: string; password: string };

// NOTE on labels: MUI appends " *" to the label of a required field, so
// `getByLabel("Password", { exact: true })` would NOT match "Password *".
// The specs therefore use the default (case-insensitive substring) matching.

/**
 * Sign in through the real /login form. The Login page navigates to "/" on
 * success, where the Home page shows a "Go to Dashboard" button.
 */
export async function loginViaUi(page: Page, user: Credentials): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Username or email").fill(user.username);
  await page.getByLabel("Password").fill(user.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("button", { name: "Go to Dashboard" })).toBeVisible();
}

/** Open the account menu in the app Navbar and click "Logout"; lands on /login. */
export async function logoutViaNavbar(page: Page, displayName: string | RegExp): Promise<void> {
  await page.getByRole("button", { name: displayName }).click();
  await page.getByRole("menuitem", { name: "Logout" }).click();
  await expect(page).toHaveURL(/\/login$/);
}

/** MUI `<TextField select>`: open the combobox and pick an option by its visible text. */
export async function selectMuiOption(
  page: Page,
  combobox: string | RegExp | Locator,
  option: string | RegExp,
): Promise<void> {
  const box = typeof combobox === "string" || combobox instanceof RegExp
    ? page.getByRole("combobox", { name: combobox })
    : combobox;
  await box.click();
  const listbox = page.getByRole("listbox");
  await expect(listbox).toBeVisible();
  await listbox.getByRole("option", { name: option, exact: typeof option === "string" }).click();
  await expect(listbox).toBeHidden();
}

/** The MUI Select combobox that is labelled by `name`. */
export function combobox(page: Page, name: string | RegExp): Locator {
  return page.getByRole("combobox", { name });
}
