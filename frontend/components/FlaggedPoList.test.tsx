import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { FlaggedPoList } from "./FlaggedPoList";
import type { FlaggedPo } from "@/lib/types";

const items: FlaggedPo[] = [
  {
    po_id: "PO-88405",
    supplier: "Anadolu Tekstil",
    category: "Womenswear",
    tier: "V2",
    tier_display: { number: 2, word: "Material" },
    qty_variance_pct: -12,
    eta_variance_days: 9,
    summary_line: "Short-ship -12% · ETA +9d",
    query: "PO-88405 came in short",
  },
  {
    po_id: "PO-88408",
    supplier: "Coastal Apparel Ltd",
    category: "Accessories",
    tier: "V3",
    tier_display: { number: 3, word: "Major" },
    qty_variance_pct: -22,
    eta_variance_days: null,
    summary_line: "Short-ship -22%",
    query: "PO-88408 wholesale short",
  },
];

describe("FlaggedPoList", () => {
  it("renders every PO with its summary", () => {
    render(<FlaggedPoList items={items} selectedPoId={null} onSelect={() => {}} />);
    expect(screen.getByText("PO-88405")).toBeInTheDocument();
    expect(screen.getByText("Short-ship -12% · ETA +9d")).toBeInTheDocument();
    expect(screen.getByText("PO-88408")).toBeInTheDocument();
  });

  it("filters by PO id or supplier", async () => {
    render(<FlaggedPoList items={items} selectedPoId={null} onSelect={() => {}} />);
    await userEvent.type(screen.getByPlaceholderText(/filter/i), "coastal");
    expect(screen.queryByText("PO-88405")).not.toBeInTheDocument();
    expect(screen.getByText("PO-88408")).toBeInTheDocument();
  });

  it("calls onSelect when a row is clicked", async () => {
    const onSelect = vi.fn();
    render(<FlaggedPoList items={items} selectedPoId={null} onSelect={onSelect} />);
    await userEvent.click(screen.getByText("PO-88405"));
    expect(onSelect).toHaveBeenCalledWith(items[0]);
  });
});
