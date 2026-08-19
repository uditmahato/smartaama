// frontend/e2e/record-advisory.spec.ts
// Update Record: severe blood pressure + urine protein "++" -> the profile's
// rule-based advisory cards show CRITICAL risk, suggest a referral and name the
// engine ("rule-based-advisory-v2").
import { expect, test } from "@playwright/test";

import { apiCreatePatient, apiLogin } from "./helpers/api";
import { getSeed, uniqueSuffix } from "./helpers/seed";
import { loginViaUi, selectMuiOption } from "./helpers/ui";

const ENGINE = "rule-based-advisory-v2";

test("severe BP + proteinuria produce a critical advisory and referral suggestion", async ({
  page,
  request,
}) => {
  const { clinician } = getSeed();
  const suffix = uniqueSuffix();

  // Setup through the API; the record entry itself is done through the UI.
  const token = await apiLogin(request, clinician.username, clinician.password);
  const patient = await apiCreatePatient(request, token, {
    first_name: "Gita",
    last_name: `Advisory${suffix}`,
    age_in_years: 31,
  });

  await loginViaUi(page, clinician);

  await test.step("baseline: no advisory data yet", async () => {
    await page.goto(`/patients/${patient.id}`);
    await expect(page.getByRole("heading", { name: `Gita Advisory${suffix}` })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Timeline (0)" })).toBeVisible();
    await expect(page.getByText("No events match the current filters.")).toBeVisible();
    // With nothing recorded the rules cannot evaluate anything -> "UNKNOWN".
    await expect(page.getByText("UNKNOWN RISK", { exact: true })).toBeVisible();
    await expect(page.getByText("No Referral Suggested", { exact: true })).toBeVisible();
  });

  await test.step("record vital signs with severe-range blood pressure", async () => {
    await page.getByRole("button", { name: "Update Medical Record" }).click();
    await expect(page).toHaveURL(new RegExp(`/patients/${patient.id}/update$`));
    await expect(page.getByRole("heading", { name: "Update Record" })).toBeVisible();

    await selectMuiOption(page, "Section", "Vital Signs");
    await expect(page.getByRole("heading", { name: "Vital Signs" })).toBeVisible();

    // Every vitals field is required by the schema.
    await page.getByLabel("Pulse Rate (bpm)").fill("88");
    await page.getByLabel("Blood Pressure (Systolic) (mmHg)").fill("165");
    await page.getByLabel("Blood Pressure (Diastolic) (mmHg)").fill("112");
    await page.getByLabel("Respiratory Rate (breaths/min)").fill("18");
    await page.getByLabel("Temperature (°C)").fill("36.8");
    await page.getByLabel("Height (cm)").fill("158");
    await page.getByLabel("Weight (kg)").fill("62");
    await page.getByLabel("Body Mass Index (BMI) (kg/m²)").fill("24.8");
    await page.getByLabel("Note (optional)").fill("E2E vitals entry");

    await page.getByRole("button", { name: "SAVE" }).click();
    await expect(page.getByRole("alert")).toContainText("Vital Signs data saved successfully!");
    // The page returns to the profile on its own after saving.
    await expect(page).toHaveURL(new RegExp(`/patients/${patient.id}$`));
  });

  await test.step("record a urine dipstick protein of ++", async () => {
    await page.goto(`/patients/${patient.id}/update?section=urine_examination`);
    await expect(page.getByRole("heading", { name: "Urine Examination" })).toBeVisible();

    await selectMuiOption(page, "Dipstick Protein", "++");
    await page.getByLabel("24-hour Urine Protein (mg/24h)").fill("450");
    await page.getByLabel("Protein:Creatinine Ratio (mg/mg)").fill("0.4");

    await page.getByRole("button", { name: "SAVE" }).click();
    await expect(page.getByRole("alert")).toContainText("Urine Examination data saved successfully!");
    await expect(page).toHaveURL(new RegExp(`/patients/${patient.id}$`));
  });

  await test.step("profile advisory cards: critical risk, referral suggested, engine named", async () => {
    // Advisory summary card
    await expect(page.getByText("Advisory Summary (rule-based)")).toBeVisible();
    await expect(page.getByText("CRITICAL RISK", { exact: true })).toBeVisible();
    await expect(page.getByText(/Severely Elevated/).first()).toBeVisible();

    // Referral advisory card
    await expect(page.getByText("Referral Advisory (rule-based)")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Referral Suggested", exact: true })).toBeVisible();
    await expect(page.getByText("CRITICAL", { exact: true })).toBeVisible(); // urgency chip
    await expect(page.getByText(/severe pre-eclampsia features/).first()).toBeVisible();

    // Both cards report which engine produced the analysis.
    await expect(page.getByText(`Engine: ${ENGINE}`)).toHaveCount(2);

    // The recorded values are on the profile: timeline rows + the note in the notes drawer.
    await expect(page.getByRole("heading", { name: "Timeline (0)" })).toHaveCount(0);
    await expect(page.getByRole("row").filter({ hasText: "Dipstick Protein" })).toContainText("++");
    await page.getByRole("button", { name: /View Notes \(\d+\)/ }).click();
    await expect(page.getByRole("heading", { name: "Notes", exact: true })).toBeVisible();
    await expect(page.getByRole("cell", { name: "E2E vitals entry" }).first()).toBeVisible();
  });
});
