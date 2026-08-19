// frontend/e2e/helpers/api.ts
// Thin API helpers for test SETUP (the thing under test is always driven
// through the browser). All URLs are absolute because the `request` fixture's
// baseURL is the frontend origin.
import type { APIRequestContext } from "@playwright/test";

import { getSeed } from "./seed";

async function fail(label: string, res: { status(): number; text(): Promise<string> }): Promise<never> {
  throw new Error(`${label} failed: HTTP ${res.status()} ${await res.text()}`);
}

/** POST /auth/login (OAuth2 password form) -> access token. */
export async function apiLogin(
  request: APIRequestContext,
  username: string,
  password: string,
): Promise<string> {
  const { apiBase } = getSeed();
  const res = await request.post(`${apiBase}/auth/login`, { form: { username, password } });
  if (!res.ok()) await fail(`login(${username})`, res);
  return ((await res.json()) as { access_token: string }).access_token;
}

export type PatientInput = {
  first_name: string;
  last_name: string;
  age_in_years?: number;
  phone_number?: string;
  province?: string;
  district?: string;
  municipality?: string;
  ward?: string;
};

/** POST /patients as the given user -> the created patient's id. */
export async function apiCreatePatient(
  request: APIRequestContext,
  token: string,
  patient: PatientInput,
): Promise<{ id: string }> {
  const { apiBase } = getSeed();
  const res = await request.post(`${apiBase}/patients`, {
    headers: { Authorization: `Bearer ${token}` },
    data: patient,
  });
  if (res.status() !== 201) await fail("POST /patients", res);
  return (await res.json()) as { id: string };
}
