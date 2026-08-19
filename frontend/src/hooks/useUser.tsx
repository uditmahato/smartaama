import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import {
  fetchMe,
  getErrorStatus,
  tokenStore,
  userStore,
  type UserInfo,
} from "../services/api";

export type UseUserResult = {
  /** Cached/fresh user, or null when unauthenticated (or not yet loaded). */
  user: UserInfo | null;
  /** True while the initial `/auth/me` request is in flight. */
  loading: boolean;
  /** True when there is no token at all (never loading in that case). */
  isAuthenticated: boolean;
  /** Re-fetch `/auth/me` and update the shared cache. */
  refresh: () => Promise<void>;
};

/**
 * Subscribes to the shared user cache and refreshes it from `/auth/me` on
 * mount. Distinguishes "still loading" from "unauthenticated" so guards can
 * show a spinner instead of redirecting prematurely.
 */
export function useUser(): UseUserResult {
  const user = useSyncExternalStore(userStore.subscribe, userStore.get);
  const hasToken = Boolean(tokenStore.get());
  const [loading, setLoading] = useState<boolean>(hasToken);

  const refresh = useCallback(async () => {
    if (!tokenStore.get()) {
      userStore.clear();
      return;
    }
    try {
      const data = await fetchMe();
      userStore.set(data);
    } catch (err) {
      // A 401 reaching us means the axios interceptor already tried to refresh
      // the access token and failed (tokens cleared + redirect to /login).
      // For other failures keep whatever is cached rather than logging out.
      if (getErrorStatus(err) === 401) userStore.clear();
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    if (!tokenStore.get()) {
      if (userStore.get()) userStore.clear();
      setLoading(false);
      return;
    }
    setLoading(true);
    refresh().finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  return {
    user,
    loading,
    isAuthenticated: hasToken,
    refresh,
  };
}
