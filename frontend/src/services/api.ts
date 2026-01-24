// frontend/src/services/api.ts
import axios, { AxiosError } from "axios";

const API_BASE_URL =
  (import.meta as any).env?.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

const TOKEN_KEY = "smart_aama_access_token";
const USER_INFO_KEY = "smart_aama_user_info";

type UserInfo = {
  id: string;
  username: string;
  full_name?: string | null;
  role: string;
  facility_type?: string | null;
  facility_id?: string | null;
  facility_name?: string | null;
};

export const tokenStore = {
  get(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  },
  set(token: string) {
    localStorage.setItem(TOKEN_KEY, token);
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_INFO_KEY);
  },
};

export const userStore = {
  get(): UserInfo | null {
    const data = localStorage.getItem(USER_INFO_KEY);
    return data ? JSON.parse(data) : null;
  },
  set(user: UserInfo) {
    localStorage.setItem(USER_INFO_KEY, JSON.stringify(user));
  },
  clear() {
    localStorage.removeItem(USER_INFO_KEY);
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
