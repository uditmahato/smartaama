// frontend/src/services/api.ts
import axios, { AxiosError } from "axios";

const API_BASE_URL =
  (import.meta as any).env?.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

const TOKEN_KEY = "smart_aama_access_token";

export const tokenStore = {
  get(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  },
  set(token: string) {
    localStorage.setItem(TOKEN_KEY, token);
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
  },
};

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

api.interceptors.response.use(
  (resp) => resp,
  (error: AxiosError) => {
    // If token expired or invalid, force logout to avoid broken UX loops
    if (error.response?.status === 401) {
      tokenStore.clear();
    }
    return Promise.reject(error);
  }
);
