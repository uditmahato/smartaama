#!/usr/bin/env node
// frontend/e2e/start-backend.mjs
//
// Playwright `webServer` command for the backend. Playwright starts web servers
// BEFORE globalSetup runs, so the "fresh database per run" guarantee lives here:
//
//   1. delete ../backend/e2e_smartaama.db (+ -journal/-wal/-shm) and ../backend/e2e_uploads
//   2. spawn  <E2E_PYTHON or python> -m uvicorn app.main:app --host 127.0.0.1 --port <E2E_BACKEND_PORT>
//      with cwd = ../backend and the environment passed in by playwright.config.ts
//      (ENV=dev, SECRET_KEY, DATABASE_URL=sqlite:///./e2e_smartaama.db, AUTO_INIT_DB=true, ...)
//
// It can also be run by hand from frontend/:  node e2e/start-backend.mjs
// (falls back to the same defaults when the env vars are missing).
//
// Set E2E_KEEP_DB=1 to skip the cleanup (debugging an existing e2e database).

import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const backendDir = path.resolve(here, "..", "..", "backend");

const DEFAULT_ENV = {
  ENV: "dev",
  SECRET_KEY: "e2e-only-secret-key-not-for-production-use-0123456789",
  DATABASE_URL: "sqlite:///./e2e_smartaama.db",
  AUTO_INIT_DB: "true",
  BOOTSTRAP_TOKEN: "e2e-bootstrap-token",
  RATE_LIMIT_DISABLED: "true",
  UPLOADS_DIR: "./e2e_uploads",
  CORS_ORIGINS: "http://localhost:5173",
};

const env = { ...process.env };
for (const [key, value] of Object.entries(DEFAULT_ENV)) {
  if (!env[key]) env[key] = value;
}

const python = env.E2E_PYTHON || "python";
const port = env.E2E_BACKEND_PORT || "8000";
const logLevel = env.E2E_BACKEND_LOG_LEVEL || "warning";

if (!fs.existsSync(path.join(backendDir, "app", "main.py"))) {
  console.error(`[e2e] backend not found at ${backendDir}`);
  process.exit(1);
}

// ---- 1. fresh state -------------------------------------------------------

function sqliteFileFromUrl(url) {
  // sqlite:///./e2e_smartaama.db  ->  ./e2e_smartaama.db (relative to backendDir)
  const m = /^sqlite:\/\/\/(.+)$/.exec(url || "");
  if (!m) return null;
  return path.resolve(backendDir, m[1]);
}

if (!env.E2E_KEEP_DB) {
  const dbFile = sqliteFileFromUrl(env.DATABASE_URL);
  if (dbFile) {
    for (const suffix of ["", "-journal", "-wal", "-shm"]) {
      const f = dbFile + suffix;
      if (fs.existsSync(f)) {
        fs.rmSync(f, { force: true });
        console.error(`[e2e] removed ${path.relative(backendDir, f)}`);
      }
    }
  }
  const uploads = path.resolve(backendDir, env.UPLOADS_DIR || "./e2e_uploads");
  // Safety: only ever delete a folder that lives inside backend/.
  if (uploads.startsWith(backendDir + path.sep) && fs.existsSync(uploads)) {
    fs.rmSync(uploads, { recursive: true, force: true });
    console.error(`[e2e] removed ${path.relative(backendDir, uploads)}${path.sep}`);
  }
}

// ---- 2. run uvicorn -------------------------------------------------------

const args = [
  "-m",
  "uvicorn",
  "app.main:app",
  "--host",
  "127.0.0.1",
  "--port",
  String(port),
  "--log-level",
  logLevel,
];

console.error(`[e2e] starting backend: ${python} ${args.join(" ")}  (cwd=${backendDir})`);

const child = spawn(python, args, {
  cwd: backendDir,
  env,
  stdio: "inherit",
  // No shell: `python` may be an absolute path with spaces on Windows.
  shell: false,
});

child.on("error", (err) => {
  console.error(`[e2e] failed to start backend with "${python}": ${err.message}`);
  console.error("[e2e] set E2E_PYTHON to the interpreter that has backend/requirements.txt installed");
  process.exit(1);
});

child.on("exit", (code, signal) => {
  if (signal) {
    console.error(`[e2e] backend exited on signal ${signal}`);
    process.exit(1);
  }
  process.exit(code ?? 0);
});

for (const sig of ["SIGINT", "SIGTERM", "SIGHUP"]) {
  process.on(sig, () => {
    if (!child.killed) child.kill(sig);
  });
}
