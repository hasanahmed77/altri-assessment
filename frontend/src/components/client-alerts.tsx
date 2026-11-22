import { Clock, Info, TriangleAlert } from "lucide-react";

import { Quote } from "@/components/quote";
import type { Alert } from "@/lib/api";

const ICONS = {
  urgent: <Clock className="mt-0.5 size-4 shrink-0 text-rose-600" />,
  warning: <TriangleAlert className="mt-0.5 size-4 shrink-0 text-amber-600" />,
  info: <Info className="text-muted-foreground mt-0.5 size-4 shrink-0" />,
};

export function ClientAlerts({ alerts }: { alerts: Alert[] }) {
  if (alerts.length === 0) return null;
  return (
    <section aria-label="Alerts" className="bg-card flex flex-col gap-2 rounded-lg border p-4">
      <h2 className="text-sm font-medium">Before you send anything</h2>
      <ul className="flex flex-col gap-2 text-sm">
        {alerts.map((alert) => (
          <li key={alert.code + alert.text} className="flex gap-2">
            {ICONS[alert.severity]}
            <span>
              {alert.text}
              <Quote quote={alert.quote} source={alert.source} />
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
