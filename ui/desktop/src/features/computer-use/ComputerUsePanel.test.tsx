import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../../services/apiClient";
import type { ComputerUseSession } from "../../types/api";
import { ComputerUsePanel } from "./ComputerUsePanel";

vi.mock("../../services/apiClient", () => ({
  apiClient: {
    listComputerUseSessions: vi.fn(),
    getComputerUseSession: vi.fn(),
    runComputerUse: vi.fn(),
    observeComputerUse: vi.fn(),
    cancelComputerUseSession: vi.fn(),
    confirmComputerUseSession: vi.fn(),
  },
}));

const waitingSession: ComputerUseSession = {
  id: "cu-1",
  goal: "Ordena las ventanas",
  status: "waiting_confirmation",
  state: {
    iteration: 0,
    plan: {
      id: "plan-1",
      steps: [
        { id: "step-1", description: "Detectar ventanas", status: "completed" },
        { id: "step-2", description: "Organizar ventanas", status: "running" },
      ],
    },
    pending_confirmation: {
      capability: "organize_windows",
      description: "Organizar las ventanas visibles",
      risk_level: "high",
    },
  },
  observations: [{ screen_summary: "Dos ventanas visibles", used_sources: ["window_manager"] }],
  actions: [],
  created_at: "2026-06-13T10:00:00",
  updated_at: "2026-06-13T10:00:01",
};

describe("ComputerUsePanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.listComputerUseSessions).mockResolvedValue({ sessions: [waitingSession] });
    vi.mocked(apiClient.getComputerUseSession).mockResolvedValue(waitingSession);
  });

  it("shows session plan, progress and resolves a pending confirmation", async () => {
    const completed = { ...waitingSession, status: "completed" } satisfies ComputerUseSession;
    vi.mocked(apiClient.confirmComputerUseSession).mockResolvedValue({
      approved: true,
      session_id: waitingSession.id,
      session: completed,
    });
    const onEvent = vi.fn();

    render(<ComputerUsePanel onEvent={onEvent} />);

    await userEvent.click(await screen.findByRole("button", { name: /Ordena las ventanas/i }));
    expect(screen.getByText("1/2 pasos")).toBeInTheDocument();
    expect(screen.getByText(/Organizar las ventanas visibles/i)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /Aprobar/i }));

    await waitFor(() => expect(apiClient.confirmComputerUseSession).toHaveBeenCalledWith("cu-1", true));
    expect(onEvent).toHaveBeenCalledWith(expect.objectContaining({ type: "computer_use.confirmed" }));
  });
});
