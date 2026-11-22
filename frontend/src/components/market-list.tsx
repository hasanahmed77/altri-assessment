import { Ban, CircleCheck, Info, TriangleAlert } from "lucide-react";

import { Quote } from "@/components/quote";
import { Card, CardContent } from "@/components/ui/card";
import type { MarketFit } from "@/lib/api";
import { pct, words } from "@/lib/format";

export function MarketList({ markets }: { markets: MarketFit[] }) {
  return (
    <div className="flex flex-col gap-4">
      <p className="text-muted-foreground text-sm">
        Every market, ranked for this client by setting, stated and spoken preferences, how many
        deals they can buy there and the returns on them.
      </p>
      {markets.map((fit) => (
        <MarketCard key={fit.market.id} fit={fit} />
      ))}
    </div>
  );
}

function MarketCard({ fit }: { fit: MarketFit }) {
  const { market } = fit;
  const supply =
    fit.eligible_deals === 0
      ? "No eligible deals right now"
      : `${fit.eligible_deals} eligible ${fit.eligible_deals === 1 ? "deal" : "deals"}` +
        (fit.median_coc_low !== null
          ? `, median ${pct(fit.median_coc_low)} CoC on low revenue`
          : "") +
        (fit.best_deal_id ? `; best is ${fit.best_deal_id}` : "");

  return (
    <Card className={fit.avoided || fit.eligible_deals === 0 ? "opacity-60" : undefined}>
      <CardContent className="flex flex-col gap-2">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <p className="font-medium">
            <span className="text-muted-foreground">#{fit.rank} · </span>
            {market.name}, {market.state}
          </p>
          <p className="text-muted-foreground text-sm">
            {words(market.setting)} · values grow ~{pct(fit.annual_appreciation)} a year
          </p>
        </div>
        <p className="text-sm">{supply}</p>
        <p className="text-muted-foreground text-sm">Travelers: {fit.typical_traveler}</p>
        {fit.reasons.length > 0 && (
          <ul className="flex flex-col gap-1 text-sm">
            {fit.reasons.map((reason) => (
              <li key={reason.code + reason.text} className="flex gap-2">
                <MarketReasonIcon code={reason.code} weight={reason.weight} />
                <span>
                  {reason.text}
                  <Quote quote={reason.quote} source={reason.source} />
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function MarketReasonIcon({ code, weight }: { code: string; weight: number }) {
  if (code === "AVOIDED_MARKET") return <Ban className="mt-0.5 size-4 shrink-0 text-rose-600" />;
  if (weight > 0) return <CircleCheck className="mt-0.5 size-4 shrink-0 text-emerald-600" />;
  if (weight < 0) return <TriangleAlert className="mt-0.5 size-4 shrink-0 text-amber-600" />;
  return <Info className="text-muted-foreground mt-0.5 size-4 shrink-0" />;
}
