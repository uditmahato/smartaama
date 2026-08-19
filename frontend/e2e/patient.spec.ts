// frontend/e2e/patient.spec.ts
// A PHC clinician registers a patient (with the Nepal province -> district ->
// municipality -> ward cascade) and lands on the patient's profile.
import { expect, test } from "@playwright/test";

import { getSeed, uniqueSuffix } from "./helpers/seed";
import { combobox, loginViaUi, selectMuiOption } from "./helpers/ui";

const ADDRESS = {
  province: "Bagmati Province",
  district: "Kathmandu",
  municipality: "Budhanilakantha",
  municipalityOption: "Budhanilakantha (Nagarpalika)",
  ward: "3",
};

test("clinician creates a patient with a Nepal address and sees the profile", async ({ page }) => {
  const { clinician, phc } = getSeed();
  const suffix = uniqueSuffix();
  const patient = { first: "Sita", last: `Testpatient${suffix}` };

  await loginViaUi(page, clinician);

  await test.step("open the Add patient form from the dashboard navbar", async () => {
    await page.getByRole("button", { name: "Go to Dashboard" }).click();
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    await page.getByRole("button", { name: "Add patient" }).click();
    await expect(page).toHaveURL(/\/patients\/new$/);
    await expect(page.getByRole("heading", { name: "Create New Patient" })).toBeVisible();
  });

  await test.step("fill in demographics and the address cascade", async () => {
    await page.getByLabel("First name").fill(patient.first);
    await page.getByLabel("Last name").fill(patient.last);
    await page.getByLabel("Age (years)", { exact: true }).fill("27");
    await page.getByLabel("Phone", { exact: true }).fill("9841234567");
    await selectMuiOption(page, "Marital Status", "Married");

    // District / municipality / ward are disabled until the parent level is chosen.
    await expect(combobox(page, "District")).toBeDisabled();
    await selectMuiOption(page, "Province", ADDRESS.province);
    await selectMuiOption(page, "District", ADDRESS.district);
    await selectMuiOption(page, /Municipality/, ADDRESS.municipalityOption);
    await selectMuiOption(page, "Ward", `Ward ${ADDRESS.ward}`);
    await page.getByLabel("Tole Name").fill("Golfutar");
  });

  await test.step("create and verify the profile", async () => {
    await page.getByRole("button", { name: "Create Patient" }).click();
    await expect(page).toHaveURL(/\/patients\/[0-9a-f-]{36}$/);

    await expect(
      page.getByRole("heading", { name: `${patient.first} ${patient.last}` }),
    ).toBeVisible();
    await expect(page.getByText("Personal Information")).toBeVisible();
    await expect(page.getByText("27 years", { exact: true })).toBeVisible();
    await expect(page.getByText(ADDRESS.district, { exact: true })).toBeVisible();
    await expect(page.getByText(ADDRESS.municipality, { exact: true })).toBeVisible();
    await expect(page.getByText("Golfutar")).toBeVisible();

    // Registered under the clinician's own facility -> full edit rights (no read-only banner).
    await expect(page.getByRole("button", { name: "Update Medical Record" })).toBeVisible();
    await expect(page.getByText("Read-Only Access:")).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Timeline (0)" })).toBeVisible();
  });

  await test.step("the patient is found by the facility-scoped search", async () => {
    await page.getByRole("button", { name: "Back" }).click();
    await expect(page).toHaveURL(/\/patients$/);
    await expect(page.getByRole("heading", { name: "Search Patients" })).toBeVisible();
    await expect(page.getByText(`${phc.name} (PHC)`)).toBeVisible();

    await page.getByLabel("Search by name / MRN / phone / national ID").fill(patient.last);
    await page.getByRole("button", { name: "Search" }).click();
    await expect(page.getByText("Results (1)")).toBeVisible();
    await expect(page.getByText(`${patient.first} ${patient.last}`)).toBeVisible();
    await expect(page.getByText("9841234567")).toBeVisible();
  });
});
