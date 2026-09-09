"use client";

import { useCallback, useEffect, useState } from "react";
import { getFlaggedPos, postTriage } from "@/lib/api";
import { FlaggedPo, TriageResponse } from "@/lib/types";
import { FlaggedPoList } from "@/components/FlaggedPoList";
import { QuestionBar } from "@/components/QuestionBar";
import { ReportPanel, ReportPhase } from "@/components/ReportPanel";

export default function Page() {
  const [items, setItems] = useState<FlaggedPo[]>([]);
  const [selected, setSelected] = useState<FlaggedPo | null>(null);
  const [question, setQuestion] = useState("");
  const [phase, setPhase] = useState<ReportPhase>("empty");
  const [result, setResult] = useState<TriageResponse | undefined>(undefined);
  const [error, setError] = useState<string | undefined>(undefined);

  useEffect(() => {
    getFlaggedPos()
      .then((response) => setItems(response.items))
      .catch((err: Error) => setError(err.message));
  }, []);

  const onSelect = useCallback((po: FlaggedPo) => {
    setSelected(po);
    setQuestion(po.query);
    setResult(undefined);
    setError(undefined);
    setPhase("empty");
  }, []);

  const onAsk = useCallback(async () => {
    setPhase("loading");
    setError(undefined);
    try {
      const response = await postTriage(question);
      setResult(response);
      setPhase("done");
    } catch (err) {
      setError((err as Error).message);
      setPhase("error");
    }
  }, [question]);

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
            onRetry={onAsk}
          />
        </div>
      </section>
    </main>
  );
}
