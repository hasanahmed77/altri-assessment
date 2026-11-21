"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import type { ClientSummary } from "@/lib/api";
import { cn } from "@/lib/utils";

export function ClientNav({ clients }: { clients: ClientSummary[] }) {
  const pathname = usePathname();

  return (
    <nav className="flex flex-col gap-1 p-2">
      {clients.map((client) => {
        const href = `/clients/${client.id}`;
        return (
          <Link
            key={client.id}
            href={href}
            className={cn(
              "rounded-md px-3 py-2 text-sm hover:bg-sidebar-accent",
              pathname === href && "bg-sidebar-accent font-medium",
            )}
          >
            <span className="flex justify-between gap-2">
              <span>{client.name}</span>
              <span className="text-muted-foreground text-xs">{client.id}</span>
            </span>
            <span className="text-muted-foreground block text-xs">{client.summary}</span>
          </Link>
        );
      })}
    </nav>
  );
}
