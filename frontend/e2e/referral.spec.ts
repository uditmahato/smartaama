// frontend/e2e/referral.spec.ts
// Referral lifecycle across two facilities:
//   PHC clinician refers a patient to the admin's hospital
//   -> clinician dashboard "Referred from Here" lists it
//   -> hospital admin opens it from the patient's referral history and marks it "Admitted Here"
//   -> status history table shows the rows, dashboard "Admitted Case" filter lists it.
import { expect, test } from "@playwright/test";

import { apiCreatePatient, apiLogin } from "./helpers/api";
import { getSeed, uniqueSuffix } from "./helpers/seed";
import { combobox, loginViaUi, selectMuiOption } from "./helpers/ui";

test("PHC refers to hospital; hospital admits; both dashboards reflect it", async ({
  page,
  browser,
  request,
}) => {
  const { clinician, admin, phc, hospital } = getSeed();
  const suffix = uniqueSuffix();
  const reason = `E2E referral ${suffix}: severe hypertension with proteinuria`;

  const token = await apiLogin(request, clinician.username, clinician.password);
  const patient = await apiCreatePatient(request, token, {
    first_name: "Maya",
    last_name: `Referral${suffix}`,
    age_in_years: 29,
  });
  const patientName = `Maya Referral${suffix}`;

  // ---------------------------------------------------------------- clinician
  await loginViaUi(page, clinician);

  await test.step("clinician creates a referral to the hospital", async () => {
    await page.goto(`/patients/${patient.id}`);
    await expect(page.getByRole("heading", { name: patientName })).toBeVisible();
    await page.getByRole("button", { name: "Refer Patient" }).click();
    await expect(page).toHaveURL(new RegExp(`/patients/${patient.id}/referral$`));
    await expect(page.getByRole("heading", { name: "Create New Referral" })).toBeVisible();

    // Non-admins are locked to their own facility as the sender.
    const from = combobox(page, "From facility");
    await expect(from).toBeDisabled();
    await expect(from).toContainText(phc.name);

    await selectMuiOption(page, "To facility", `${hospital.name} (Hos)`);
    await page.getByLabel("Referral reason").fill(reason);
    await page.getByLabel("Clinician note (optional)").fill("BP 165/112, dipstick ++");

    await page.getByRole("button", { name: "Create Referral" }).click();

    await expect(page.getByRole("heading", { name: "Referral Created" })).toBeVisible();
    await expect(page.getByText("Status (Referring)", { exact: true })).toBeVisible();
    await expect(page.getByText("Referred from Here", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Pending acknowledgment")).toBeVisible();
    await expect(page.getByText(hospital.name, { exact: true })).toBeVisible();

    // History table already has the "Created" row.
    await expect(page.getByRole("heading", { name: "Status History" })).toBeVisible();
    await expect(page.getByRole("row").filter({ hasText: "Created" })).toBeVisible();
  });

  await test.step('clinician dashboard: "Referred from Here" lists the referral', async () => {
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    await selectMuiOption(page, "Status", "Referred from Here");
    await expect(page.getByText("Status: Referred from Here")).toBeVisible();

    const card = page.getByText(reason).locator("xpath=ancestor::div[contains(@class,'MuiCard-root')][1]");
    await expect(card).toBeVisible();
    await expect(card).toContainText(`${phc.name} → ${hospital.name}`);
    await expect(card).toContainText("Referred from Here");
  });

  // -------------------------------------------------------------------- admin
  const adminContext = await browser.newContext();
  const adminPage = await adminContext.newPage();

  try {
    await loginViaUi(adminPage, admin);

    await test.step("hospital admin opens the referral from the patient's referral history", async () => {
      await adminPage.goto(`/patients/${patient.id}`);
      await expect(adminPage.getByRole("heading", { name: patientName })).toBeVisible();

      await adminPage.getByRole("button", { name: "View Referral History (1)" }).click();
      const drawerRow = adminPage.getByRole("row").filter({ hasText: phc.name }).filter({ hasText: hospital.name });
      await expect(drawerRow).toBeVisible();
      await drawerRow.click();

      await expect(adminPage).toHaveURL(new RegExp(`/patients/${patient.id}/referral/[0-9a-f-]{36}$`));
      await expect(adminPage.getByRole("heading", { name: "Referral Created" })).toBeVisible();
      await expect(adminPage.getByText(reason)).toBeVisible();
    });

    await test.step('admin marks the referral "Admitted Here"', async () => {
      // The admin's facility is the receiving hospital -> receiving-side controls.
      await expect(
        adminPage.getByRole("heading", { name: "Update Your Status (Received Place)" }),
      ).toBeVisible();

      const save = adminPage.getByRole("button", { name: "Save Status" });
      await expect(save).toBeDisabled();
      await selectMuiOption(adminPage, "Your facility status", "Admitted Here");
      await adminPage.getByLabel("Add note (optional)").fill("Admitted to maternity ward");
      await expect(save).toBeEnabled();
      await save.click();

      // Received-place status chip + mirrored referring status.
      await expect(adminPage.getByText("Status (Received Place)", { exact: true })).toBeVisible();
      await expect(adminPage.getByText("Admitted Here", { exact: true }).first()).toBeVisible();
      await expect(adminPage.getByText(`Referred to ${hospital.name}`, { exact: true })).toBeVisible();

      // History table: created -> receiving status "Admitted Here" (with note)
      //                        -> referring status mirrored to "Referred to Here".
      const rows = adminPage.getByRole("row");
      await expect(rows.filter({ hasText: "Created" })).toBeVisible();
      const receivedRow = rows.filter({ hasText: "Receiving status" });
      await expect(receivedRow).toBeVisible();
      await expect(receivedRow).toContainText("Admitted Here");
      await expect(receivedRow).toContainText("Admitted to maternity ward");
      await expect(receivedRow).toContainText(admin.full_name);
      const mirroredRow = rows.filter({ hasText: "Referring status" });
      await expect(mirroredRow).toBeVisible();
      await expect(mirroredRow).toContainText("Referred to Here");
    });

    await test.step('admin dashboard: "Admitted Case" lists the referral', async () => {
      await adminPage.goto("/dashboard");
      await expect(adminPage.getByRole("heading", { name: "Dashboard" })).toBeVisible();
      await selectMuiOption(adminPage, "Status", "Admitted Case");
      await expect(adminPage.getByText("Status: Admitted Case")).toBeVisible();

      const card = adminPage.getByText(reason).locator("xpath=ancestor::div[contains(@class,'MuiCard-root')][1]");
      await expect(card).toBeVisible();
      await expect(card).toContainText(`${phc.name} → ${hospital.name}`);
      await expect(card).toContainText(`Referred to ${hospital.name}`);

      // Clicking the card opens the patient's profile.
      await card.click();
      await expect(adminPage).toHaveURL(new RegExp(`/patients/${patient.id}$`));
    });
  } finally {
    await adminContext.close();
  }

  await test.step("clinician sees the admitted status on the referral", async () => {
    await page.goto(`/patients/${patient.id}`);
    await page.getByRole("button", { name: "View Referral History (1)" }).click();
    const drawerRow = page.getByRole("row").filter({ hasText: hospital.name });
    await expect(drawerRow).toContainText("Referred to Here");
    await drawerRow.click();
    await expect(page.getByRole("heading", { name: "Referral Created" })).toBeVisible();
    // Sender view: received-place status is read-only.
    await expect(page.getByText("Received Place Status", { exact: true })).toBeVisible();
    await expect(page.getByText("Admitted Here", { exact: true }).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Update Status (Referring)" })).toBeVisible();
  });
});
