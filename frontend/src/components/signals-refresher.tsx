"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

const INTERVAL_MS = 2000;
const MAX_TRIES = 5;

// New comments are read in the background. Rendered only while that is happening: it refreshes
// the page a few times, stops when the fresh page no longer renders it, and gives up after
// MAX_TRIES so a slow model never leaves the page polling.
export function SignalsRefresher() {
  const router = useRouter();

  useEffect(() => {
    let tries = 0;
    const timer = setInterval(() => {
      tries += 1;
      router.refresh();
      if (tries >= MAX_TRIES) clearInterval(timer);
    }, INTERVAL_MS);
    return () => clearInterval(timer);
  }, [router]);

  return null;
}
