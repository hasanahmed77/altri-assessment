import { ExcludedDealCard, RankedDealCard } from "@/components/deal-cards";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { RankedDeal, Recommendations } from "@/lib/api";

const SHOWN_FIRST = 5;

export function DealTabs({ recommendations }: { recommendations: Recommendations }) {
  const { client_id: clientId, ranked, excluded } = recommendations;
  const toSend = ranked.filter((r) => r.status !== "already_shared");
  const shared = ranked.filter((r) => r.status === "already_shared");

  return (
    <Tabs defaultValue="recommended">
      <TabsList>
        <TabsTrigger value="recommended">Recommended ({toSend.length})</TabsTrigger>
        <TabsTrigger value="shared">Already shared ({shared.length})</TabsTrigger>
        <TabsTrigger value="excluded">Ruled out ({excluded.length})</TabsTrigger>
      </TabsList>

      <TabsContent value="recommended" className="flex flex-col gap-4">
        <DealList items={toSend.slice(0, SHOWN_FIRST)} clientId={clientId} />
        {toSend.length > SHOWN_FIRST && (
          <details className="group">
            <summary className="text-muted-foreground cursor-pointer text-sm">
              Show {toSend.length - SHOWN_FIRST} more eligible deals
            </summary>
            <div className="mt-4">
              <DealList
                items={toSend.slice(SHOWN_FIRST)}
                clientId={clientId}
                firstPosition={SHOWN_FIRST + 1}
              />
            </div>
          </details>
        )}
        {toSend.length === 0 && <Empty text="No eligible deals left to send." />}
      </TabsContent>

      <TabsContent value="shared">
        <DealList items={shared} clientId={clientId} />
        {shared.length === 0 && <Empty text="No deals shared yet." />}
      </TabsContent>

      <TabsContent value="excluded" className="flex flex-col gap-4">
        <p className="text-muted-foreground text-sm">
          These break at least one hard rule, so they are never recommended.
        </p>
        {excluded.map((item) => (
          <ExcludedDealCard key={item.deal.id} item={item} />
        ))}
      </TabsContent>
    </Tabs>
  );
}

function DealList({
  items,
  clientId,
  firstPosition = 1,
}: {
  items: RankedDeal[];
  clientId: string;
  firstPosition?: number;
}) {
  return (
    <div className="flex flex-col gap-4">
      {items.map((item, index) => (
        <RankedDealCard
          key={item.deal.id}
          item={item}
          clientId={clientId}
          position={firstPosition + index}
        />
      ))}
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <p className="text-muted-foreground py-8 text-center text-sm">{text}</p>;
}
