import { ThumbsDown, ThumbsUp } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ClientDetail } from "@/lib/api";
import { pct, usd, words } from "@/lib/format";

export function ClientSummary({ client }: { client: ClientDetail }) {
  const settings = Object.entries(client.setting_rank)
    .sort(([, a], [, b]) => a - b)
    .map(([setting]) => words(setting));

  const facts: [string, string][] = [
    ["Budget", `${usd(client.budget)} (${client.budget_flexibility}), stated range ${client.budget_range}`],
    ["Financing", `${pct(client.down_payment_pct, 0)} down, ${pct(client.cohost_fee_pct, 0)} co-host fee`],
    ["Main focus", words(client.main_focus)],
    ["Bedrooms", `${client.min_bedrooms}+`],
    ["Settings, in order", settings.join(" › ")],
    ["Renovation appetite", client.renovation_appetite],
    ["Wants turnkey", client.wants_turnkey ? "yes" : "no"],
    ["Wow factors", client.wow_factors.join(", ") || "none given"],
    ["Onboarded", client.onboarded_at],
  ];

  return (
    <div className="grid gap-4 lg:grid-cols-[3fr_2fr]">
      <Card>
        <CardHeader>
          <CardTitle className="text-xl">
            {client.name} <span className="text-muted-foreground text-sm">{client.id}</span>
          </CardTitle>
          {client.notes && <p className="text-muted-foreground text-sm">“{client.notes}”</p>}
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
            {facts.map(([term, value]) => (
              <div key={term} className="contents">
                <dt className="text-muted-foreground">{term}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
          <MarketTerms
            label="Preferred markets"
            terms={client.preferred_markets}
            unresolved={client.unresolved_markets}
          />
          <MarketTerms
            label="Avoided markets"
            terms={client.avoid_markets}
            unresolved={client.unresolved_markets}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Activity</CardTitle>
        </CardHeader>
        <CardContent className="flex max-h-96 flex-col gap-4 overflow-y-auto text-sm">
          <section>
            <h3 className="mb-2 font-medium">Calls</h3>
            {client.calls.length === 0 && <p className="text-muted-foreground">No calls yet</p>}
            <ul className="flex flex-col gap-2">
              {client.calls.map((call) => (
                <li key={call.call_date + call.summary}>
                  <span className="text-muted-foreground text-xs">{call.call_date}</span>
                  <p>{call.summary}</p>
                </li>
              ))}
            </ul>
          </section>
          <section>
            <h3 className="mb-2 font-medium">Feedback</h3>
            {client.feedback.length === 0 && (
              <p className="text-muted-foreground">No feedback yet</p>
            )}
            <ul className="flex flex-col gap-2">
              {client.feedback.map((item) => (
                <li key={item.id} className="flex gap-2">
                  {item.reaction === "up" ? (
                    <ThumbsUp className="mt-0.5 size-4 shrink-0 text-emerald-600" />
                  ) : (
                    <ThumbsDown className="mt-0.5 size-4 shrink-0 text-rose-600" />
                  )}
                  <span>
                    <span className="font-medium">{item.deal_id}</span>{" "}
                    <span className="text-muted-foreground text-xs">{item.created_at}</span>
                    {item.comment && <span className="block">{item.comment}</span>}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        </CardContent>
      </Card>
    </div>
  );
}

function MarketTerms({
  label,
  terms,
  unresolved,
}: {
  label: string;
  terms: string[];
  unresolved: string[];
}) {
  return (
    <div className="text-sm">
      <p className="text-muted-foreground mb-1">{label}</p>
      <div className="flex flex-wrap gap-1">
        {terms.length === 0 && <span>none</span>}
        {terms.map((term) =>
          unresolved.includes(term) ? (
            <Badge key={term} variant="outline" title="Not one of STR Search's markets">
              {term} · no matching market
            </Badge>
          ) : (
            <Badge key={term} variant="secondary">
              {term}
            </Badge>
          ),
        )}
      </div>
    </div>
  );
}
