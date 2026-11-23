"use client";

import { LoaderCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const INTERVAL_MS = 2000;
const MAX_TRIES = 5;

// New comments are read in the background. Rendered only while that is happening: it refreshes
// the page a few times, stops when the fresh page no longer renders it, and gives up after
// MAX_TRIES so a slow model never leaves the page polling. Fixed on screen because the rep is
// usually down on a deal card when they record a comment.
export function SignalsRefresher() {
  const router = useRouter();
  const [gaveUp, setGaveUp] = useState(false);

  useEffect(() => {
    let tries = 0;
    const timer = setInterval(() => {
      tries += 1;
      router.refresh();
      if (tries >= MAX_TRIES) {
        clearInterval(timer);
        setGaveUp(true);
      }
    }, INTERVAL_MS);
    return () => clearInterval(timer);
  }, [router]);

  return (
    <div
      role="status"
      className="bg-background fixed bottom-6 left-1/2 z-50 flex -translate-x-1/2 items-center gap-2 rounded-full border px-4 py-2 text-sm shadow-lg"
    >
      {gaveUp ? (
        "Still reading the comment; reload in a moment to see what it changed"
      ) : (
        <>
          <LoaderCircle className="size-4 animate-spin text-amber-600" />
          AI is reading the client&apos;s comment; this page will update by itself
        </>
      )}
    </div>
  );
}
