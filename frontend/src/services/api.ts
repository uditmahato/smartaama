// frontend/src/services/api.ts
import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import type {
  AdvisoryAnalysis,
  ReferralHistoryOut,
  UserInfo,
  UserOut,
} from "./types";

export type {
  AdvisoryAnalysis,
  ReferralHistoryOut,
  ReferralOut,
  ReferralStatus,
  UserInfo,
  UserOut,
} from "./types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

const TOKEN_KEY = "smart_aama_access_token";
const REFRESH_TOKEN_KEY = "smart_aama_refresh_token";
const USER_INFO_KEY = "smart_aama_user_info";
const LOGIN_PATH = "/login";
// Pages that work without a session; a stale token there is just dropped.
const PUBLIC_PATHS = new Set(["/", LOGIN_PATH, "/signup"]);

// ---- Token store ----------------------------------------------------------
//
// Both tokens live in localStorage. Trade-off: any script running on this
// origin (XSS) can read them; the hardening path is to move the refresh token
// into an httpOnly, SameSite cookie set by the backend (and keep only the
// short-lived access token in memory). Mitigations in place today: the access
// token is short-lived (ACCESS_TOKEN_EXPIRE_MINUTES), the refresh token is
// single-use (rotated on every /auth/refresh) and a replay of a rotated token
// revokes the whole token family server-side.

export const tokenStore = {
  /** Access token (Bearer). */
  get(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  },
  /** Refresh token (opaque, single-use). */
  getRefresh(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },
  /** Store an access token; pass the matching refresh token when you have one. */
  set(token: string, refreshToken?: string | null) {
    localStorage.setItem(TOKEN_KEY, token);
    if (refreshToken) localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  },
  /** Clears both tokens AND the cached user (logout). */
  clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    userStore.clear();
  },
};

// ---- User store (localStorage-backed, subscribable) ------------------------

type Listener = () => void;
const userListeners = new Set<Listener>();
// `undefined` = not read from localStorage yet; `null` = no cached user.
let cachedUser: UserInfo | null | undefined;

function readCachedUser(): UserInfo | null {
  const raw = localStorage.getItem(USER_INFO_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as UserInfo;
  } catch {
    localStorage.removeItem(USER_INFO_KEY);
    return null;
  }
}

function notifyUserListeners() {
  userListeners.forEach((l) => l());
}

export const userStore = {
  /** Returns a stable reference until the next set()/clear(). */
  get(): UserInfo | null {
    if (cachedUser === undefined) cachedUser = readCachedUser();
    return cachedUser;
  },
  set(user: UserInfo) {
    cachedUser = user;
    localStorage.setItem(USER_INFO_KEY, JSON.stringify(user));
    notifyUserListeners();
  },
  clear() {
    cachedUser = null;
    localStorage.removeItem(USER_INFO_KEY);
    notifyUserListeners();
  },
  subscribe(listener: Listener): () => void {
    userListeners.add(listener);
    return () => {
      userListeners.delete(listener);
    };
  },
};

// ---- Axios instance -------------------------------------------------------

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
});

api.interceptors.request.use((config) => {
  const token = tokenStore.get();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ---- Session (login / refresh / logout) -----------------------------------

/** Body of POST /auth/login and POST /auth/refresh. */
export type TokenResponse = {
  access_token: string;
  token_type: string; // "bearer"
  /** Access-token lifetime in seconds. */
  expires_in: number;
  refresh_token: string;
};

// Auth endpoints whose own 401 must NOT trigger a refresh (bad credentials /
// dead refresh token) — otherwise we would loop.
const AUTH_URLS = ["/auth/login", "/auth/refresh", "/auth/logout"];

function isAuthUrl(url: string | undefined): boolean {
  return Boolean(url) && AUTH_URLS.some((p) => (url as string).includes(p));
}

// A request config that has already been retried once after a refresh.
type RetriableConfig = InternalAxiosRequestConfig & { _retried?: boolean };

// Single-flight refresh: concurrent 401s share ONE /auth/refresh call. The
// refresh token is single-use on the server, so two parallel refreshes would
// make the second one look like a replay and revoke the whole session.
let refreshInflight: Promise<string> | null = null;

/**
 * Exchange the stored refresh token for a new access + refresh pair (rotation).
 * Resolves with the new access token; rejects when there is no refresh token or
 * the server refuses it. Uses a bare axios call so the interceptors below don't
 * recurse. Concurrent callers share the in-flight request.
 */
export function refreshAccessToken(): Promise<string> {
  if (refreshInflight) return refreshInflight;
  const staleRefresh = tokenStore.getRefresh();
  if (!staleRefresh) return Promise.reject(new Error("No refresh token"));

  refreshInflight = withCrossTabLock(async () => {
    // Another tab may have rotated the tokens while we waited for the lock:
    // if the stored tokens changed, reuse them instead of presenting the
    // (now single-use, already rotated) old refresh token.
    const currentAccess = tokenStore.get();
    const currentRefresh = tokenStore.getRefresh();
    if (currentAccess && currentRefresh && currentRefresh !== staleRefresh) {
      return currentAccess;
    }
    if (!currentRefresh) throw new Error("No refresh token");
    const resp = await axios.post<TokenResponse>(
      `${API_BASE_URL}/auth/refresh`,
      { refresh_token: currentRefresh },
      { timeout: 20000 },
    );
    tokenStore.set(resp.data.access_token, resp.data.refresh_token);
    return resp.data.access_token;
  }).finally(() => {
    refreshInflight = null;
  });
  return refreshInflight;
}

/**
 * Serialise token refreshes across browser tabs (they share localStorage and
 * therefore one single-use refresh token). Uses the Web Locks API where
 * available; otherwise falls back to running immediately (per-tab single flight).
 */
function withCrossTabLock<T>(fn: () => Promise<T>): Promise<T> {
  const locks = (
    typeof navigator !== "undefined"
      ? (navigator as Navigator & { locks?: LockManager }).locks
      : undefined
  );
  if (locks && typeof locks.request === "function") {
    // LockManager.request's callback type is loosely typed; the promise resolves with fn's value.
    return locks.request("smartaama-token-refresh", async () => fn()) as Promise<T>;
  }
  return fn();
}

/** POST /auth/login (OAuth2 password form) — stores both tokens on success. */
export async function login(
  username: string,
  password: string,
): Promise<TokenResponse> {
  const body = new URLSearchParams();
  body.set("username", username.trim());
  body.set("password", password);
  body.set("grant_type", "");
  body.set("scope", "");
  body.set("client_id", "");
  body.set("client_secret", "");
  const resp = await api.post<TokenResponse>("/auth/login", body, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  tokenStore.set(resp.data.access_token, resp.data.refresh_token);
  return resp.data;
}

/**
 * Logout: revoke the refresh token on the server (best effort — the local
 * session is cleared whether or not the request succeeds), then clear tokens +
 * cached user. Never throws.
 */
export async function logout(): Promise<void> {
  const refreshToken = tokenStore.getRefresh();
  // Clear first so no in-flight interceptor can refresh with the dying token.
  tokenStore.clear();
  if (!refreshToken) return;
  try {
    await axios.post(
      `${API_BASE_URL}/auth/logout`,
      { refresh_token: refreshToken },
      { timeout: 10000 },
    );
  } catch {
    // Best effort: the token expires on its own; nothing to show the user.
  }
}

function endSessionAndRedirect() {
  tokenStore.clear();
  if (
    typeof window !== "undefined" &&
    !PUBLIC_PATHS.has(window.location.pathname)
  ) {
    window.location.assign(LOGIN_PATH);
  }
}

api.interceptors.response.use(
  (resp) => resp,
  async (error: AxiosError) => {
    if (error.response?.status !== 401) return Promise.reject(error);

    const config = error.config as RetriableConfig | undefined;
    const url = config?.url ?? "";
    // A 401 from login/refresh/logout means "bad credentials" / "dead refresh
    // token": leave the page alone so the caller can show the error.
    if (!config || isAuthUrl(url)) return Promise.reject(error);

    // Any other 401 means the access token is missing/expired/revoked. Try ONE
    // refresh (single-flight across concurrent 401s) and retry the request once
    // with the new token; if that is not possible, end the session.
    if (!config._retried && tokenStore.getRefresh()) {
      config._retried = true;
      try {
        const newToken = await refreshAccessToken();
        config.headers = config.headers ?? {};
        config.headers.Authorization = `Bearer ${newToken}`;
        return api.request(config);
      } catch {
        // fall through: refresh failed (expired / revoked / offline)
      }
    }
    endSessionAndRedirect();
    return Promise.reject(error);
  },
);

// ---- Error helpers --------------------------------------------------------

/** HTTP status of an axios error, or undefined for non-HTTP errors. */
export function getErrorStatus(err: unknown): number | undefined {
  return axios.isAxiosError(err) ? err.response?.status : undefined;
}

export function isForbidden(err: unknown): boolean {
  return getErrorStatus(err) === 403;
}

export function isNotFound(err: unknown): boolean {
  return getErrorStatus(err) === 404;
}

/**
 * Human-readable message for an API/JS error.
 * Prefers FastAPI's `detail` (string or 422 validation list), then falls back.
 */
export function getErrorMessage(
  err: unknown,
  fallback = "Something went wrong. Please try again.",
): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as { detail?: unknown } | undefined;
    const detail = data?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
    if (Array.isArray(detail)) {
      const msgs = detail
        .map((d) =>
          d && typeof d === "object" && typeof (d as { msg?: unknown }).msg === "string"
            ? ((d as { msg: string }).msg)
            : null,
        )
        .filter((m): m is string => Boolean(m));
      if (msgs.length) return msgs.join("; ");
    }
    if (err.response?.status === 403) {
      return "You don't have access to this resource.";
    }
    if (!err.response) {
      return "Could not reach the server. Check your connection and try again.";
    }
    return fallback;
  }
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}

// ---- Facility helpers -----------------------------------------------------

/** Case-insensitive, trimmed facility-name comparison (mirrors backend authz). */
export function facilityMatches(
  a: string | null | undefined,
  b: string | null | undefined,
): boolean {
  if (!a || !b) return false;
  const na = a.trim().toLowerCase();
  const nb = b.trim().toLowerCase();
  return na.length > 0 && na === nb;
}

// ---- Typed endpoint helpers ----------------------------------------------

let meInflight: Promise<UserInfo> | null = null;

/** GET /auth/me — concurrent callers share one in-flight request. */
export function fetchMe(): Promise<UserInfo> {
  if (!meInflight) {
    meInflight = api
      .get<UserOut>("/auth/me")
      .then((resp) => resp.data)
      .finally(() => {
        meInflight = null;
      });
  }
  return meInflight;
}

// Admin / users
export async function fetchAdminUsers(): Promise<UserOut[]> {
  const resp = await api.get<UserOut[]>("/admin/users");
  return resp.data;
}

export async function fetchPendingUsers(): Promise<UserOut[]> {
  const resp = await api.get<UserOut[]>("/admin/users/pending");
  return resp.data;
}

/** GET /admin/users/rejected — registrations an admin rejected (approve re-admits). */
export async function fetchRejectedUsers(): Promise<UserOut[]> {
  const resp = await api.get<UserOut[]>("/admin/users/rejected");
  return resp.data;
}

export async function approveUser(userId: string): Promise<void> {
  await api.patch(`/admin/users/${userId}/approve`);
}

export async function rejectUser(userId: string): Promise<void> {
  await api.patch(`/admin/users/${userId}/reject`);
}

export async function deleteUser(userId: string): Promise<void> {
  await api.delete(`/admin/users/${userId}`);
}

/** GET /admin/users/{id}/id-card — authenticated image download as a Blob. */
export async function fetchUserIdCardBlob(userId: string): Promise<Blob> {
  const resp = await api.get<Blob>(`/admin/users/${userId}/id-card`, {
    responseType: "blob",
  });
  return resp.data;
}

// Referrals
export async function fetchReferralHistory(
  referralId: string,
): Promise<ReferralHistoryOut[]> {
  const resp = await api.get<ReferralHistoryOut[]>(
    `/referrals/${referralId}/history`,
  );
  return resp.data;
}

// Advisory analysis (rule-based)
export async function fetchAdvisoryAnalysis(
  patientId: string,
  opts: { forceRegenerate?: boolean } = {},
): Promise<AdvisoryAnalysis> {
  const resp = await api.get<AdvisoryAnalysis>(
    `/ai-analysis/patients/${patientId}/analysis`,
    {
      params: {
        auto_generate: true,
        ...(opts.forceRegenerate ? { force_regenerate: true } : {}),
      },
    },
  );
  return resp.data;
}
