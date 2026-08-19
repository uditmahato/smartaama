// frontend/e2e/screenshots.spec.ts
// Captures the README screenshots against the throw-away E2E stack.
// Skipped unless E2E_SCREENSHOTS=1, so it never runs as part of `npm run test:e2e` in CI:
//
//   E2E_SCREENSHOTS=1 npx playwright test e2e/screenshots.spec.ts
//
// Output: documentation/screenshots/*.png (viewport 1400x900).
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "@playwright/test";

import { apiCreatePatient, apiLogin } from "./helpers/api";
import { getSeed, uniqueSuffix } from "./helpers/seed";
import { loginViaUi } from "./helpers/ui";

const here = path.dirname(fileURLToPath(import.meta.url));
const OUT_DIR = path.resolve(here, "..", "..", "documentation", "screenshots");

test.skip(!process.env.E2E_SCREENSHOTS, "set E2E_SCREENSHOTS=1 to capture README screenshots");

async function shot(page: import("@playwright/test").Page, name: string, fullPage = false) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  await page.waitForLoadState("networkidle");
  await page.screenshot({ path: path.join(OUT_DIR, `${name}.png`), fullPage });
}

test("capture README screenshots", async ({ browser, request }) => {
  test.setTimeout(180_000);
  const seed = getSeed();
  const suffix = uniqueSuffix();

  // ---- seed data via API (setup only) -------------------------------------------------
  const clinToken = await apiLogin(request, seed.clinician.username, seed.clinician.password);
  const adminToken = await apiLogin(request, seed.admin.username, seed.admin.password);
  const auth = (t: string) => ({ Authorization: `Bearer ${t}` });

  const patient = await apiCreatePatient(request, clinToken, {
    first_name: "Sunita",
    last_name: `Tamang-${suffix}`,
    age_in_years: 26,
    phone_number: "9841000000",
    province: "Bagmati Province",
    district: "Kathmandu",
    municipality: "Budhanilakantha",
    ward: "3",
  });

  const md = async (section: string, data: Record<string, unknown>) => {
    const res = await request.post(`${seed.apiBase}/medical-data/patients/${patient.id}/sections/${section}`, {
      headers: auth(clinToken),
      data: { section_key: section, data_points: data },
    });
    expect(res.status(), await res.text()).toBe(201);
  };
  await md("vitals", {
    blood_pressure_systolic: 165,
    blood_pressure_diastolic: 112,
    pulse_rate: 96,
    temperature: 37.1,
    respiratory_rate: 18,
  });
  await md("urine_examination", { dipstick_protein: "++" });
  await md("blood_investigations", { hemoglobin: 9.4 });

  const refRes = await request.post(`${seed.apiBase}/referrals`, {
    headers: auth(clinToken),
    data: {
      patient_id: patient.id,
      from_facility: seed.phc.name,
      to_facility: seed.hospital.name,
      reason: "Severe hypertension with proteinuria at 32 weeks — advisory suggests urgent review.",
      status: "submitted",
    },
  });
  expect(refRes.status(), await refRes.text()).toBe(201);
  const referral = (await refRes.json()) as { id: string };

  const admit = await request.post(`${seed.apiBase}/referrals/${referral.id}/received-status`, {
    headers: auth(adminToken),
    data: { received_facility_status: "received", note: "Admitted to maternity ward; BP monitoring started." },
  });
  expect(admit.status(), await admit.text()).toBe(200);

  // ---- clinician views ---------------------------------------------------------------
  const clinCtx = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  const page = await clinCtx.newPage();
  await loginViaUi(page, seed.clinician);

  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible();
  await shot(page, "dashboard");

  await page.goto(`/patients/${patient.id}`);
  await expect(page.getByText(/rule-based-advisory/i).first()).toBeVisible();
  await expect(page.getByText(/critical/i).first()).toBeVisible();
  await shot(page, "patient-profile");
  // The two advisory cards as element screenshots (a full-page capture is >5000px tall).
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const summaryCard = page.locator(".MuiCard-root").filter({ hasText: "Advisory Summary (rule-based)" }).first();
  await summaryCard.scrollIntoViewIfNeeded();
  await summaryCard.screenshot({ path: path.join(OUT_DIR, "advisory-summary.png") });
  const referralCard = page.locator(".MuiCard-root").filter({ hasText: "Referral Advisory (rule-based)" }).first();
  await referralCard.scrollIntoViewIfNeeded();
  await referralCard.screenshot({ path: path.join(OUT_DIR, "referral-advisory.png") });

  await page.goto(`/patients/${patient.id}/referral/${referral.id}`);
  await expect(page.getByText(/Admitted Here/i).first()).toBeVisible();
  const historyHeading = page.getByText(/history/i).first();
  await historyHeading.scrollIntoViewIfNeeded();
  await shot(page, "referral-history");

  await clinCtx.close();

  // ---- admin view ---------------------------------------------------------------------
  const adminCtx = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  const apage = await adminCtx.newPage();
  await loginViaUi(apage, seed.admin);
  await apage.goto("/admin/pending");
  await expect(apage.getByRole("heading", { name: /pending/i })).toBeVisible();
  await shot(apage, "admin-pending-users");
  await adminCtx.close();
});
