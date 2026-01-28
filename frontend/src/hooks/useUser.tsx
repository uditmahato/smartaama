import { useEffect, useState } from "react";
import { fetchMe, userStore } from "../services/api";

export function useUser() {
  const [user, setUser] = useState(userStore.get());

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchMe();
        userStore.set(data);
        setUser(data);
      } catch (err) {
        userStore.clear();
        setUser(null);
      }
    }

    load();
  }, []);

  return user;
}
