import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ConfirmationModal } from "./ConfirmationModal";

describe("ConfirmationModal", () => {
  it("renders payload and confirms", async () => {
    const onConfirm = vi.fn();
    render(
      <ConfirmationModal
        payload={{ tool_name: "list_directory", arguments: { path: "." }, risk_level: "medium" }}
        onConfirm={onConfirm}
        onReject={vi.fn()}
      />,
    );

    expect(screen.getByText("list_directory")).toBeInTheDocument();
    await userEvent.click(screen.getByText("Confirmar ejecucion"));
    expect(onConfirm).toHaveBeenCalled();
  });
});
