// frontend/e2e/auth.spec.ts
// Login page: bad credentials show an error, good credentials land on "/" and
// the dashboard is reachable; protected routes bounce anonymous users to /login.
import { expect, test } from "@playwright/test";

import { getSeed } from "./helpers/seed";
import { loginViaUi } from "./helpers/ui";

test.describe("authentication", () => {
  test("shows an error for a wrong password and stays on /login", async ({ page }) => {
    const { admin } = getSeed();

    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "SmartAama" })).toBeVisible();

    const signIn = page.getByRole("button", { name: "Sign in" });
    await expect(signIn).toBeDisabled(); // nothing typed yet

    await page.getByLabel("Username or email").fill(admin.username);
    await page.getByLabel("Password").fill("definitely-not-the-password");
    await signIn.click();

    await expect(page.getByRole("alert")).toContainText("Incorrect username or password");
    await expect(page).toHaveURL(/\/login$/);
    await expect(signIn).toBeEnabled();
  });

  test("logs in with valid credentials and reaches the dashboard", async ({ page }) => {
    const { admin } = getSeed();

    await loginViaUi(page, admin);

    await page.getByRole("button", { name: "Go to Dashboard" }).click();
    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    // Navbar shows who is signed in and their facility.
    await expect(page.getByText(`${admin.facility_name} (Hos)`)).toBeVisible();
  });

  test("redirects anonymous visitors from a protected page to /login", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
  });
});
