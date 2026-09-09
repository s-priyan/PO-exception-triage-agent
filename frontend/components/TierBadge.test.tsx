import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TierBadge } from "./TierBadge";

describe("TierBadge", () => {
  it("renders number only by default", () => {
    render(<TierBadge number={2} word="Material" />);
    expect(screen.getByText("TIER 2")).toBeInTheDocument();
  });

  it("renders number and word when withWord is set", () => {
    render(<TierBadge number={2} word="Material" withWord />);
    expect(screen.getByText("TIER 2 · MATERIAL")).toBeInTheDocument();
  });
});
