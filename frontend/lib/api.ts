import { API_BASE_URL } from "./config";
import { FlaggedPosResponse, TriageResponse } from "./types";

export async function getFlaggedPos(
  signal?: AbortSignal,
): Promise<FlaggedPosResponse> {
  const response = await fetch(`${API_BASE_URL}/flagged-pos`, { signal });
  if (!response.ok) {
    throw new Error(`Failed to load flagged POs (${response.status})`);
  }
  return response.json();
}

export async function postTriage(
  question: string,
  signal?: AbortSignal,
): Promise<TriageResponse> {
  const response = await fetch(`${API_BASE_URL}/triage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal,
  });
  if (!response.ok) {
    throw new Error(`Triage failed (${response.status})`);
  }
  return response.json();
}
