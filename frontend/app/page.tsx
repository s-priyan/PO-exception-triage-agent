"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getFlaggedPos, postTriage } from "@/lib/api";
import { FlaggedPo, TriageResponse } from "@/lib/types";
import { FlaggedPoList } from "@/components/FlaggedPoList";
import { QuestionBar } from "@/components/QuestionBar";
import { ReportPanel, ReportPhase } from "@/components/ReportPanel";

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong.";
}

export default function Page() {
  const [items, setItems] = useState<FlaggedPo[]>([]);
  const [selected, setSelected] = useState<FlaggedPo | null>(null);
  const [question, setQuestion] = useState("");
  const [phase, setPhase] = useState<ReportPhase>("empty");
  const [result, setResult] = useState<TriageResponse | undefined>(undefined);
  const [error, setError] = useState<string | undefined>(undefined);

  // Monotonic id so only the latest user action is allowed to commit state;
  // triage is slow, so a stale response must not overwrite a newer selection.
  const requestId = useRef(0);

  const loadPos = useCallback(() => {
    requestId.current += 1;
    getFlaggedPos()
      .then((response) => setItems(response.items))
      .catch((err: unknown) => {
        setError(errorMessage(err));
        setPhase("error");
      });
  }, []);

  useEffect(() => {
    loadPos();
  }, [loadPos]);

  const onSelect = useCallback((po: FlaggedPo) => {
    requestId.current += 1; // invalidate any in-flight triage
    setSelected(po);
    setQuestion(po.query);
    setResult(undefined);
    setError(undefined);
    setPhase("empty");
  }, []);

  const onAsk = useCallback(async () => {
    const id = (requestId.current += 1);
    setPhase("loading");
    setError(undefined);
    try {
      const response = await postTriage(question);
      if (id !== requestId.current) return; // superseded by a newer action
      setResult(response);
      setPhase("done");
    } catch (err) {
      if (id !== requestId.current) return;
      setError(errorMessage(err));
      setPhase("error");
    }
  }, [question]);

  const onRetry = useCallback(() => {
    if (items.length === 0) {
      setError(undefined);
      setPhase("empty");
      loadPos();
    } else {
      onAsk();
    }
  }, [items.length, loadPos, onAsk]);

  return (
    <main className="flex h-screen">
      <FlaggedPoList
        items={items}
        selectedPoId={selected?.po_id ?? null}
        onSelect={onSelect}
      />
      <section className="flex min-w-0 flex-1 flex-col">
        <QuestionBar
          value={question}
          onChange={setQuestion}
          onAsk={onAsk}
          loading={phase === "loading"}
        />
        <div className="min-h-0 flex-1 overflow-y-auto">
          <ReportPanel
            phase={phase}
            result={result}
            error={error}
            selectedPoId={selected?.po_id ?? null}
            onRetry={onRetry}
          />
        </div>
      </section>
    </main>
  );
}
