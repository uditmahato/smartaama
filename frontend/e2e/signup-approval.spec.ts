// frontend/e2e/signup-approval.spec.ts
// Self-registration -> pending -> admin approval -> the new clinician can log in.
import { expect, test } from "@playwright/test";

import { tinyPngFile } from "./helpers/files";
import { getSeed, uniqueSuffix } from "./helpers/seed";
import { loginViaUi, logoutViaNavbar, selectMuiOption } from "./helpers/ui";

test("a clinician registers, is approved by an admin, then signs in", async ({ page, browser }) => {
  const { admin, phc } = getSeed();
  const suffix = uniqueSuffix();
  const newUser = {
    username: `e2e-signup-${suffix}@example.com`,
    password: `Signup-pass-${suffix}-1234`,
    full_name: `Signup Clinician ${suffix}`,
  };

  await test.step("register through the Signup page (PHC, with ID-card upload)", async () => {
    await page.goto("/signup");
    await expect(page.getByRole("heading", { name: "Register" })).toBeVisible();

    await page.getByLabel("Email").fill(newUser.username);
    await page.getByLabel("Password (min 10 characters)").fill(newUser.password);
    await page.getByLabel("Full Name").fill(newUser.full_name);
    await page.getByLabel("Phone Number").fill("9811111111");
    await page.getByLabel("Nepal Medical Council Number").fill(`NMC-${suffix}`);
    await page.getByLabel("Currently Working Hospital").fill(phc.name);

    // The ID-card upload is required by the form (`canRegister`).
    await page.locator('input[type="file"]').setInputFiles(tinyPngFile("id-card.png"));
    await expect(page.getByText("Selected: id-card.png")).toBeVisible();

    await page.getByRole("radio", { name: "PHC" }).check();
    await selectMuiOption(page, "Select PHC", phc.name);

    const register = page.getByRole("button", { name: "Register", exact: true });
    await expect(register).toBeEnabled();
    await register.click();

    await expect(page.getByRole("alert")).toContainText("Registration successful! Awaiting approval by admin.");
    await expect(page).toHaveURL(/\/login$/);
  });

  await test.step("the pending account cannot sign in yet", async () => {
    await page.getByLabel("Username or email").fill(newUser.username);
    await page.getByLabel("Password").fill(newUser.password);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByRole("alert")).toContainText("Your account is not approved yet");
    await expect(page).toHaveURL(/\/login$/);
  });

  await test.step("admin approves the registration in /admin/pending", async () => {
    await loginViaUi(page, admin);
    await page.goto("/admin/pending");
    await expect(page.getByRole("heading", { name: "Pending Users" })).toBeVisible();

    const row = page.getByRole("row").filter({ hasText: newUser.username });
    await expect(row).toBeVisible();
    await expect(row).toContainText(phc.name);
    await row.getByRole("button", { name: "Approve" }).click();

    await expect(page.getByText(`Approved ${newUser.full_name}.`)).toBeVisible();
    await expect(row).toHaveCount(0);

    await logoutViaNavbar(page, admin.full_name);
  });

  await test.step("the approved clinician can sign in and sees their PHC in the navbar", async () => {
    // Fresh browser context: no leftover token / cached user from the admin session.
    const context = await browser.newContext();
    const clinicianPage = await context.newPage();
    try {
      await loginViaUi(clinicianPage, newUser);
      await clinicianPage.getByRole("button", { name: "Go to Dashboard" }).click();
      await expect(clinicianPage).toHaveURL(/\/dashboard$/);
      await expect(clinicianPage.getByText(newUser.full_name)).toBeVisible();
      await expect(clinicianPage.getByText(`${phc.name} (PHC)`)).toBeVisible();
      // Non-admins do not get the admin navigation.
      await expect(clinicianPage.getByRole("button", { name: "Pending Users" })).toHaveCount(0);
    } finally {
      await context.close();
    }
  });
});
