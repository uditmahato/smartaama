// frontend/e2e/helpers/seed.ts
// Access to the accounts/facilities created by global-setup.ts.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export type Facility = { id: string; name: string; kind: "phc" | "hospital" };

export type SeedUser = {
  username: string;
  password: string;
  full_name: string;
  facility_name: string;
  facility_kind: "phc" | "hospital";
};

export type Seed = {
  apiBase: string;
  hospital: Facility;
  phc: Facility;
  /** Super admin at `hospital` (created via /auth/bootstrap-admin). */
  admin: SeedUser;
  /** Approved clinician at `phc` (registered + approved via the API). */
  clinician: SeedUser;
};

/** Relative to frontend/. Written by global-setup.ts (after Playwright cleared test-results/). */
export const SEED_FILE = "test-results/e2e-seed.json";

let cached: Seed | null = null;

export function getSeed(): Seed {
  if (cached) return cached;
  if (process.env.E2E_SEED) {
    cached = JSON.parse(process.env.E2E_SEED) as Seed;
    return cached;
  }
  const here = path.dirname(fileURLToPath(import.meta.url));
  const file = path.resolve(here, "..", "..", SEED_FILE);
  if (!fs.existsSync(file)) {
    throw new Error(`E2E seed not found (${file}). Did global-setup run? Use "npx playwright test", not a bare test runner.`);
  }
  cached = JSON.parse(fs.readFileSync(file, "utf8")) as Seed;
  return cached;
}

/** Short unique suffix so names/emails never collide across runs or workers. */
export function uniqueSuffix(): string {
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
}
