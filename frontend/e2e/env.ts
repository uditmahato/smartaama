// frontend/e2e/env.ts
// Single source of truth for the ports / URLs / backend environment used by
// playwright.config.ts, global-setup.ts and the spec helpers.

// Ports can be overridden (e.g. when another dev server already occupies 5173):
//   E2E_BACKEND_PORT=8010 E2E_FRONTEND_PORT=5199 npm run test:e2e
function portFromEnv(name: string, fallback: number): number {
  const raw = process.env[name];
  const n = raw ? Number(raw) : NaN;
  return Number.isInteger(n) && n > 0 && n < 65536 ? n : fallback;
}
export const BACKEND_PORT = portFromEnv("E2E_BACKEND_PORT", 8000);
export const FRONTEND_PORT = portFromEnv("E2E_FRONTEND_PORT", 5173);

// The backend is addressed as 127.0.0.1 (not "localhost") on purpose: on some
// machines another process holds [::1]:8000 and Chromium/Node would connect to
// that first. The page origin stays http://localhost:5173 (CORS allow-list).
export const BACKEND_ORIGIN = `http://127.0.0.1:${BACKEND_PORT}`;
export const API_BASE = `${BACKEND_ORIGIN}/api/v1`;
export const FRONTEND_ORIGIN = `http://localhost:${FRONTEND_PORT}`;

export const BOOTSTRAP_TOKEN = "e2e-bootstrap-token";

/** Environment for the backend process (dev-only, throw-away values). */
export const BACKEND_ENV: Record<string, string> = {
  ENV: "dev",
  SECRET_KEY: "e2e-only-secret-key-not-for-production-use-0123456789",
  DATABASE_URL: "sqlite:///./e2e_smartaama.db",
  AUTO_INIT_DB: "true",
  BOOTSTRAP_TOKEN,
  RATE_LIMIT_DISABLED: "true",
  UPLOADS_DIR: "./e2e_uploads",
  CORS_ORIGINS: FRONTEND_ORIGIN,
  // Consumed by e2e/start-backend.mjs (not by the app itself).
  E2E_BACKEND_PORT: String(BACKEND_PORT),
};

/** Deterministic admin created by global setup via POST /auth/bootstrap-admin. */
export const ADMIN_CREDENTIALS = {
  username: "e2e-admin@example.com",
  password: "E2E-admin-pass-12345",
  full_name: "E2E Admin",
};

/** PHC clinician seeded by global setup (register + approve via the API). */
export const CLINICIAN_CREDENTIALS = {
  username: "e2e-clinician@example.com",
  password: "E2E-clinician-pass-12345",
  full_name: "E2E Clinician",
};
