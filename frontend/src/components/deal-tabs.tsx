"use client";

import { X } from "lucide-react";
import { Fragment, useRef, useState } from "react";

import { ExcludedDealCard, RankedDealCard } from "@/components/deal-cards";
import { MarketList } from "@/components/market-list";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { MarketFit, RankedDeal, Recommendations } from "@/lib/api";

const SHOWN_FIRST = 5;
// A client who hasn't picked a market, or whose markets have nothing to buy, needs a
// conversation about where before a list of deals
const WHERE_FIRST = new Set(["UNDECIDED_MARKET", "NO_DEALS_IN_PREFERRED"]);

export function DealTabs({
  recommendations,
  markets,
}: {
  recommendations: Recommendations;
  markets: MarketFit[];
}) {
  const { client_id: clientId, ranked, excluded, alerts } = recommendations;
  const toSend = ranked.filter((r) => r.status !== "already_shared");
  const shared = ranked.filter((r) => r.status === "already_shared");
  const closeCallsFirst = [...excluded].sort(
    (a, b) => Number(b.near_miss !== null) - Number(a.near_miss !== null),
  );
  const whereFirst = alerts.some((a) => WHERE_FIRST.has(a.code));
  const firstOutside = toSend.find((r) => r.outside_client_markets)?.deal.id;

  const [tab, setTab] = useState(whereFirst ? "markets" : "recommended");
  const [marketId, setMarketId] = useState<string | null>(null);
  const top = useRef<HTMLDivElement>(null);
  const selectedMarket = markets.find((m) => m.market.id === marketId)?.market;
  const inMarket = toSend.filter((r) => r.deal.market.id === marketId);
  const toSendByMarket: Record<string, number> = {};
  for (const r of toSend) {
    toSendByMarket[r.deal.market.id] = (toSendByMarket[r.deal.market.id] ?? 0) + 1;
  }

  function seeHouses(id: string) {
    setMarketId(id);
    setTab("recommended");
    top.current?.scrollIntoView({ block: "start" });
  }

  return (
    <div ref={top} className="scroll-mt-4">
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="flex-wrap">
          <TabsTrigger value="recommended">Recommended ({toSend.length})</TabsTrigger>
          <TabsTrigger value="markets">Where to buy</TabsTrigger>
          <TabsTrigger value="shared">Already shared ({shared.length})</TabsTrigger>
          <TabsTrigger value="excluded">Ruled out ({excluded.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="markets">
          <MarketList markets={markets} toSendByMarket={toSendByMarket} onSeeHouses={seeHouses} />
        </TabsContent>

        <TabsContent value="recommended" className="flex flex-col gap-4">
          {selectedMarket ? (
            <>
              <div className="flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm">
                <span>
                  Showing {selectedMarket.name}, {selectedMarket.state} · {inMarket.length} of{" "}
                  {toSend.length} deals, in this client&apos;s ranked order
                </span>
                <Button variant="ghost" size="sm" onClick={() => setMarketId(null)}>
                  <X /> Clear
                </Button>
              </div>
              {inMarket.map((item) => (
                <RankedDealCard
                  key={item.deal.id}
                  item={item}
                  clientId={clientId}
                  position={toSend.indexOf(item) + 1}
                />
              ))}
              {inMarket.length === 0 && <Empty text="No deals left to send in this market." />}
            </>
          ) : (
            <>
              <DealList
                items={toSend.slice(0, SHOWN_FIRST)}
                clientId={clientId}
                dividerBefore={firstOutside}
              />
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
                      dividerBefore={firstOutside}
                    />
                  </div>
                </details>
              )}
            </>
          )}
          {toSend.length === 0 && <Empty text="No eligible deals left to send." />}
        </TabsContent>

        <TabsContent value="shared">
          <DealList items={shared} clientId={clientId} />
          {shared.length === 0 && <Empty text="No deals shared yet." />}
        </TabsContent>

        <TabsContent value="excluded" className="flex flex-col gap-4">
          <p className="text-muted-foreground text-sm">
            These break at least one hard rule, so they are never recommended. Close calls come
            first: a small price cut would make them pass.
          </p>
          {closeCallsFirst.map((item) => (
            <ExcludedDealCard key={item.deal.id} item={item} />
          ))}
        </TabsContent>
      </Tabs>
    </div>
  );
}

function DealList({
  items,
  clientId,
  firstPosition = 1,
  dividerBefore,
}: {
  items: RankedDeal[];
  clientId: string;
  firstPosition?: number;
  dividerBefore?: string;
}) {
  return (
    <div className="flex flex-col gap-4">
      {items.map((item, index) => (
        <Fragment key={item.deal.id}>
          {item.deal.id === dividerBefore && (
            <p className="text-muted-foreground border-t pt-3 text-sm">
              Outside the markets this client named, best first
            </p>
          )}
          <RankedDealCard item={item} clientId={clientId} position={firstPosition + index} />
        </Fragment>
      ))}
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <p className="text-muted-foreground py-8 text-center text-sm">{text}</p>;
}
