import type { components } from "@/lib/api-types";

type Schemas = components["schemas"];
export type ClientSummary = Schemas["ClientSummaryOut"];
export type ClientDetail = Schemas["ClientDetailOut"];
export type Recommendations = Schemas["RecommendationsOut"];
export type RankedDeal = Schemas["RankedDealOut"];
export type ExcludedDeal = Schemas["ExcludedDealOut"];
export type Deal = Schemas["DealOut"];
export type DealNumbers = Schemas["NumbersOut"];
export type FeedbackIn = Schemas["FeedbackIn"];
export type Feedback = Schemas["FeedbackOut"];
export type Reason = Schemas["ReasonOut"];
export type Alert = Schemas["AlertOut"];
export type Signal = Schemas["SignalOut"];
export type SignalsStatus = Recommendations["signals_status"];
export type MarketFit = Schemas["MarketFitOut"];

// Only server code (Server Components and Server Actions) imports this module,
// so the API address never reaches the browser
const API_URL = process.env.API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = typeof body?.detail === "string" ? body.detail : response.statusText;
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

export const api = {
  clients: () => request<ClientSummary[]>("/clients"),
  client: (id: string) => request<ClientDetail>(`/clients/${encodeURIComponent(id)}`),
  recommendations: (id: string) =>
    request<Recommendations>(`/clients/${encodeURIComponent(id)}/recommendations`),
  markets: (id: string) => request<MarketFit[]>(`/clients/${encodeURIComponent(id)}/markets`),
  createFeedback: (body: FeedbackIn) =>
    request<Feedback>("/feedback", { method: "POST", body: JSON.stringify(body) }),
};
