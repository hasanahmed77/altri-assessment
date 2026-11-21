import type { Deal, DealNumbers } from "@/lib/api";
import { pct, usd } from "@/lib/format";

export function DealHeading({ deal, position }: { deal: Deal; position?: number }) {
  return (
    <div>
      <p className="font-medium">
        {position !== undefined && <span className="text-muted-foreground">#{position} · </span>}
        {deal.id} · {deal.address}, {deal.city} {deal.state}
      </p>
      <p className="text-muted-foreground text-sm">
        {deal.market.name} · {usd(deal.purchase_price)} · {deal.bedrooms ?? "?"} bd /{" "}
        {deal.baths} ba · setup {usd(deal.setup_cost)}
      </p>
    </div>
  );
}

export function DealStats({ numbers }: { numbers: DealNumbers }) {
  const { coc } = numbers;
  return (
    <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
      <Stat label="Cash needed" value={usd(numbers.cash_needed)} />
      <Stat label="CoC low" value={pct(coc.low)} hint="Cash-on-cash return in a slow year" />
      <Stat label="CoC mid" value={pct(coc.mid)} hint="Expected cash-on-cash return" />
      <Stat label="CoC high" value={pct(coc.high)} hint="Cash-on-cash return in a strong year" />
    </dl>
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="bg-muted/50 rounded-md px-3 py-2" title={hint}>
      <dt className="text-muted-foreground text-xs">{label}</dt>
      <dd className="font-medium tabular-nums">{value}</dd>
    </div>
  );
}
