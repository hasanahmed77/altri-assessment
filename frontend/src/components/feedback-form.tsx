"use client";

import { ThumbsDown, ThumbsUp } from "lucide-react";
import { useActionState, useEffect } from "react";
import { toast } from "sonner";

import { type FeedbackState, submitFeedback } from "@/app/actions";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

const initialState: FeedbackState = { status: "idle", message: "" };

export function FeedbackForm({ clientId, dealId }: { clientId: string; dealId: string }) {
  const [state, formAction, pending] = useActionState(submitFeedback, initialState);

  useEffect(() => {
    if (state.status === "saved") toast.success(state.message);
    if (state.status === "error") toast.error(state.message);
  }, [state]);

  return (
    <form action={formAction} className="flex flex-col gap-2">
      <input type="hidden" name="client_id" value={clientId} />
      <input type="hidden" name="deal_id" value={dealId} />
      <Textarea
        name="comment"
        rows={2}
        maxLength={1000}
        placeholder="Client's comment (optional), saved with the reaction below"
        aria-label={`Comment on ${dealId}`}
      />
      <div className="flex gap-2">
        <Button
          type="submit"
          name="reaction"
          value="up"
          variant="outline"
          size="icon"
          aria-label="Thumbs up"
          title="Thumbs up"
          disabled={pending}
        >
          <ThumbsUp />
        </Button>
        <Button
          type="submit"
          name="reaction"
          value="down"
          variant="outline"
          size="icon"
          aria-label="Thumbs down"
          title="Thumbs down"
          disabled={pending}
        >
          <ThumbsDown />
        </Button>
      </div>
    </form>
  );
}
