import { LoaderCircle } from "lucide-react";

import { Quote } from "@/components/quote";
import { SignalsRefresher } from "@/components/signals-refresher";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { Signal, SignalsStatus } from "@/lib/api";

const STATUS: Record<SignalsStatus, string | null> = {
  fresh: null,
  updating: "Reading new comments…",
  stale: "Out of date: new comments haven't been read (no API key)",
  unavailable: "Not read yet (no API key)",
};

export function ClientSignals({ signals, status }: { signals: Signal[]; status: SignalsStatus }) {
  const note = STATUS[status];
  return (
    <Card>
      <CardHeader>
        <CardTitle>What the client said</CardTitle>
        <CardDescription>
          Read from notes, calls and comments by an AI model. Every item quotes its source; anything
          that couldn&apos;t be found word for word was dropped.
        </CardDescription>
        {note && (
          <p className="flex items-center gap-2 text-sm text-amber-700">
            {status === "updating" && <LoaderCircle className="size-4 animate-spin" />}
            {note}
          </p>
        )}
        {status === "updating" && <SignalsRefresher />}
      </CardHeader>
      <CardContent>
        {signals.length === 0 ? (
          <p className="text-muted-foreground text-sm">Nothing beyond the profile.</p>
        ) : (
          <ul className="grid gap-3 text-sm sm:grid-cols-2">
            {signals.map((signal) => (
              <li key={signal.kind + signal.text + signal.source} className="flex flex-col gap-0.5">
                <span>
                  <Badge variant="outline" className="mr-2">
                    {signal.kind}
                  </Badge>
                  {signal.text}
                </span>
                <Quote quote={signal.quote} source={signal.source} />
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
