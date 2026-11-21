"use server";

import { refresh } from "next/cache";

import { ApiError, api } from "@/lib/api";

export type FeedbackState = {
  status: "idle" | "saved" | "error";
  message: string;
};

// Authentication is out of scope for this assessment; a real deployment would check
// that the signed-in rep owns this client before writing.
export async function submitFeedback(
  _previous: FeedbackState,
  formData: FormData,
): Promise<FeedbackState> {
  const reaction = formData.get("reaction");
  if (reaction !== "up" && reaction !== "down") {
    return { status: "error", message: "Choose thumbs up or thumbs down" };
  }

  try {
    await api.createFeedback({
      client_id: String(formData.get("client_id")),
      deal_id: String(formData.get("deal_id")),
      reaction,
      comment: String(formData.get("comment") ?? ""),
    });
  } catch (error) {
    const message = error instanceof ApiError ? error.message : "Could not save feedback";
    return { status: "error", message };
  }

  refresh();
  return { status: "saved", message: `Thumbs ${reaction} saved; recommendations updated` };
}
