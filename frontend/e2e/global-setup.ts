// frontend/e2e/global-setup.ts
//
// Runs once after Playwright has started both web servers and before any spec.
// Seeds the accounts every spec relies on (idempotent, so it also works against
// a reused server / existing e2e database):
//
//   1. GET  /facilities?kind=hospital|phc      -> pick the first hospital and PHC
//   2. POST /auth/bootstrap-admin (X-Bootstrap-Token) -> admin at that hospital
//   3. POST /auth/register (multipart, PHC) + PATCH /admin/users/{id}/approve
//      -> an approved PHC clinician (used by the patient/record/referral specs;
//         the signup spec registers ANOTHER user through the UI)
//
// The resulting seed (credentials + facilities) is exposed to the specs via
// process.env.E2E_SEED and test-results/e2e-seed.json (see helpers/seed.ts).
import { request, type APIRequestContext, type FullConfig } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { ADMIN_CREDENTIALS, API_BASE, BOOTSTRAP_TOKEN, CLINICIAN_CREDENTIALS } from "./env";
import { tinyPngBuffer } from "./helpers/files";
import { SEED_FILE, type Facility, type Seed } from "./helpers/seed";

const here = path.dirname(fileURLToPath(import.meta.url));

async function readJson<T>(res: Awaited<ReturnType<APIRequestContext["get"]>>): Promise<T> {
  const text = await res.text();
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(`Expected JSON from ${res.url()} (status ${res.status()}), got: ${text.slice(0, 300)}`);
  }
}

async function listFacilities(api: APIRequestContext, kind: "phc" | "hospital"): Promise<Facility[]> {
  const res = await api.get(`${API_BASE}/facilities`, { params: { kind } });
  if (!res.ok()) {
    throw new Error(`GET /facilities?kind=${kind} failed: ${res.status()} ${await res.text()}`);
  }
  const rows = await readJson<Facility[]>(res);
  if (!rows.length) throw new Error(`No ${kind} facilities seeded — is AUTO_INIT_DB=true on the backend?`);
  return rows;
}

async function login(api: APIRequestContext, username: string, password: string): Promise<string> {
  const res = await api.post(`${API_BASE}/auth/login`, { form: { username, password } });
  if (!res.ok()) {
    throw new Error(`POST /auth/login for ${username} failed: ${res.status()} ${await res.text()}`);
  }
  const body = await readJson<{ access_token: string }>(res);
  return body.access_token;
}

async function ensureAdmin(api: APIRequestContext, hospital: Facility): Promise<string> {
  const res = await api.post(`${API_BASE}/auth/bootstrap-admin`, {
    headers: { "X-Bootstrap-Token": BOOTSTRAP_TOKEN },
    data: {
      username: ADMIN_CREDENTIALS.username,
      password: ADMIN_CREDENTIALS.password,
      full_name: ADMIN_CREDENTIALS.full_name,
      facility_kind: "hospital",
      facility_id: hospital.id,
    },
  });
  if (res.status() === 201) {
    console.log(`[e2e] bootstrapped admin ${ADMIN_CREDENTIALS.username} @ ${hospital.name}`);
  } else if (res.status() === 400 && (await res.text()).includes("User already exists")) {
    console.log(`[e2e] admin ${ADMIN_CREDENTIALS.username} already exists (reusing database)`);
  } else {
    throw new Error(
      `POST /auth/bootstrap-admin failed: ${res.status()} ${await res.text()}\n` +
        "The backend must run with ENV=dev and BOOTSTRAP_TOKEN=e2e-bootstrap-token (see e2e/README.md).",
    );
  }
  // Sanity: the credentials must work before any spec depends on them.
  return login(api, ADMIN_CREDENTIALS.username, ADMIN_CREDENTIALS.password);
}

async function ensureClinician(api: APIRequestContext, adminToken: string, phc: Facility): Promise<void> {
  const res = await api.post(`${API_BASE}/auth/register`, {
    multipart: {
      email: CLINICIAN_CREDENTIALS.username,
      password: CLINICIAN_CREDENTIALS.password,
      full_name: CLINICIAN_CREDENTIALS.full_name,
      phone_number: "9800000000",
      nmc_number: "NMC-E2E-0001",
      working_hospital: phc.name,
      facility_type: "phc",
      facility_id: phc.id,
      id_card_image: { name: "id-card.png", mimeType: "image/png", buffer: tinyPngBuffer() },
    },
  });

  if (res.status() === 201) {
    const body = await readJson<{ user: { id: string } }>(res);
    const approve = await api.patch(`${API_BASE}/admin/users/${body.user.id}/approve`, {
      headers: { Authorization: `Bearer ${adminToken}` },
    });
    if (!approve.ok()) {
      throw new Error(`PATCH /admin/users/${body.user.id}/approve failed: ${approve.status()} ${await approve.text()}`);
    }
    console.log(`[e2e] registered + approved clinician ${CLINICIAN_CREDENTIALS.username} @ ${phc.name}`);
  } else if (res.status() === 400 && (await res.text()).includes("User already exists")) {
    console.log(`[e2e] clinician ${CLINICIAN_CREDENTIALS.username} already exists (reusing database)`);
  } else {
    throw new Error(`POST /auth/register failed: ${res.status()} ${await res.text()}`);
  }

  // Sanity: must be able to log in (i.e. approved + active).
  await login(api, CLINICIAN_CREDENTIALS.username, CLINICIAN_CREDENTIALS.password);
}

export default async function globalSetup(_config: FullConfig): Promise<void> {
  const api = await request.newContext({ timeout: 30_000 });
  try {
    const hospitals = await listFacilities(api, "hospital");
    const phcs = await listFacilities(api, "phc");
    const hospital = hospitals[0];
    const phc = phcs[0];

    const adminToken = await ensureAdmin(api, hospital);
    await ensureClinician(api, adminToken, phc);

    const seed: Seed = {
      apiBase: API_BASE,
      hospital,
      phc,
      admin: { ...ADMIN_CREDENTIALS, facility_name: hospital.name, facility_kind: "hospital" },
      clinician: { ...CLINICIAN_CREDENTIALS, facility_name: phc.name, facility_kind: "phc" },
    };

    // Available to every worker via env; the file is a fallback (and handy for debugging).
    process.env.E2E_SEED = JSON.stringify(seed);
    const seedPath = path.resolve(here, "..", SEED_FILE);
    fs.mkdirSync(path.dirname(seedPath), { recursive: true });
    fs.writeFileSync(seedPath, JSON.stringify(seed, null, 2));
  } finally {
    await api.dispose();
  }
}
