import { Ban, CircleCheck, HandCoins, Info, TriangleAlert } from "lucide-react";

import { DealHeading, DealStats } from "@/components/deal-parts";
import { FeedbackForm } from "@/components/feedback-form";
import { Quote } from "@/components/quote";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { ExcludedDeal, RankedDeal } from "@/lib/api";

export function RankedDealCard({
  item,
  clientId,
  position,
}: {
  item: RankedDeal;
  clientId: string;
  position: number;
}) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <DealHeading deal={item.deal} position={position} />
          <StatusBadge item={item} />
        </div>
        <DealStats numbers={item.numbers} />
        <ul className="flex flex-col gap-1 text-sm">
          {item.explanation.map((reason) => (
            <li key={reason.code + reason.text} className="flex gap-2">
              <ReasonIcon weight={reason.weight} />
              <span>
                {reason.text}
                <Quote quote={reason.quote} source={reason.source} />
              </span>
            </li>
          ))}
        </ul>
        <FeedbackForm clientId={clientId} dealId={item.deal.id} />
      </CardContent>
    </Card>
  );
}

export function ExcludedDealCard({ item }: { item: ExcludedDeal }) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <DealHeading deal={item.deal} />
          {item.near_miss && <Badge variant="outline">Close call</Badge>}
        </div>
        <ul className="flex flex-col gap-1 text-sm">
          {item.violations.map((violation) => (
            <li key={violation.code} className="flex gap-2">
              <Ban className="mt-0.5 size-4 shrink-0 text-rose-600" />
              <span>{violation.message}</span>
            </li>
          ))}
          {item.near_miss && (
            <li className="flex gap-2">
              <HandCoins className="mt-0.5 size-4 shrink-0 text-emerald-600" />
              <span>{item.near_miss.text}</span>
            </li>
          )}
        </ul>
        <DealStats numbers={item.numbers} />
      </CardContent>
    </Card>
  );
}

function StatusBadge({ item }: { item: RankedDeal }) {
  if (item.status === "alternative_plan") return <Badge variant="outline">Alternative plan</Badge>;
  if (item.status === "already_shared") {
    return item.reaction === "up" ? (
      <Badge variant="secondary">Shared · client liked</Badge>
    ) : (
      <Badge variant="destructive">Shared · client passed</Badge>
    );
  }
  return <Badge>New</Badge>;
}

function ReasonIcon({ weight }: { weight: number }) {
  if (weight > 0) return <CircleCheck className="mt-0.5 size-4 shrink-0 text-emerald-600" />;
  if (weight < 0) return <TriangleAlert className="mt-0.5 size-4 shrink-0 text-amber-600" />;
  return <Info className="text-muted-foreground mt-0.5 size-4 shrink-0" />;
}
