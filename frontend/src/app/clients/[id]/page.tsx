import { notFound } from "next/navigation";
import { Suspense } from "react";

import { ClientAlerts } from "@/components/client-alerts";
import { ClientSignals } from "@/components/client-signals";
import { ClientSummary } from "@/components/client-summary";
import { DealTabs } from "@/components/deal-tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, api } from "@/lib/api";

// Not async: the shell renders immediately and the client's data streams in fresh on
// every request, because recommendations change whenever feedback is recorded.
export default function ClientPage({ params }: PageProps<"/clients/[id]">) {
  return (
    <Suspense fallback={<ClientPageSkeleton />}>
      <ClientView params={params} />
    </Suspense>
  );
}

async function ClientView({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [client, recommendations, markets] = await Promise.all([
    api.client(id),
    api.recommendations(id),
    api.markets(id),
  ]).catch((error: unknown) => {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  });

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <ClientAlerts alerts={recommendations.alerts} />
      <ClientSummary client={client} />
      <ClientSignals signals={recommendations.signals} status={recommendations.signals_status} />
      <DealTabs key={id} recommendations={recommendations} markets={markets} />
    </div>
  );
}

function ClientPageSkeleton() {
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <Skeleton className="h-64 w-full" />
      <Skeleton className="h-10 w-80" />
      <Skeleton className="h-56 w-full" />
      <Skeleton className="h-56 w-full" />
    </div>
  );
}
