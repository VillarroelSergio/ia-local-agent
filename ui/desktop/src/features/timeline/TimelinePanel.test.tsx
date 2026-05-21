import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TimelinePanel } from "./TimelinePanel";

describe("TimelinePanel", () => {
  it("renders readable audit events", () => {
    render(<TimelinePanel events={[{ type: "tool.completed", data: { name: "get_system_info" } }]} />);
    expect(screen.getByText("Tool completada")).toBeInTheDocument();
    expect(screen.getByTestId("timeline-list")).toBeInTheDocument();
  });
});
