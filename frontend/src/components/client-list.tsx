import { ClientNav } from "@/components/client-nav";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";

export async function ClientList() {
  const clients = await api.clients();
  return <ClientNav clients={clients} />;
}

export function ClientListSkeleton() {
  return (
    <div className="flex flex-col gap-2 p-3">
      {Array.from({ length: 8 }, (_, i) => (
        <Skeleton key={i} className="h-12 w-full" />
      ))}
    </div>
  );
}
