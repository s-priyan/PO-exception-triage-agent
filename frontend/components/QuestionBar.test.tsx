import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { QuestionBar } from "./QuestionBar";

describe("QuestionBar", () => {
  it("disables Ask when empty", () => {
    render(
      <QuestionBar value="   " onChange={() => {}} onAsk={() => {}} loading={false} />,
    );
    expect(screen.getByRole("button", { name: /ask/i })).toBeDisabled();
  });

  it("calls onAsk when clicked with text", async () => {
    const onAsk = vi.fn();
    render(
      <QuestionBar value="PO-88405?" onChange={() => {}} onAsk={onAsk} loading={false} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /ask/i }));
    expect(onAsk).toHaveBeenCalledOnce();
  });
});
