import { Activity, Brain, MonitorCog, Wrench } from "lucide-react";
import { useState } from "react";
import { ComputerUsePanel } from "../features/computer-use/ComputerUsePanel";
import { MemoryStatus } from "../features/settings/MemoryStatus";
import { ToolsPanel } from "../features/tools/ToolsPanel";
import { TimelinePanel } from "../features/timeline/TimelinePanel";
import type { ConfirmationPayload, TimelineEvent } from "../types/api";

type PanelTab = "tools" | "memory" | "computer" | "activity";

interface Props {
  conversationId?: string;
  events: TimelineEvent[];
  onEvent: (event: Record<string, unknown>) => void;
  onConfirmation: (payload: ConfirmationPayload) => void;
}

/** Controla las pestanas laterales de tools, memoria y actividad de la conversacion actual. */
export function RightPanel({ conversationId, events, onEvent, onConfirmation }: Props) {
  const [tab, setTab] = useState<PanelTab>("tools");

  return (
    <aside className="right-panel">
      <nav className="panel-tabs" aria-label="Panel derecho">
        <button className={tab === "tools" ? "active" : ""} onClick={() => setTab("tools")}>
          <Wrench size={16} />
          Tools
        </button>
        <button className={tab === "memory" ? "active" : ""} onClick={() => setTab("memory")}>
          <Brain size={16} />
          Memoria
        </button>
        <button className={tab === "computer" ? "active" : ""} onClick={() => setTab("computer")}>
          <MonitorCog size={16} />
          PC
        </button>
        <button className={tab === "activity" ? "active" : ""} onClick={() => setTab("activity")}>
          <Activity size={16} />
          Actividad
        </button>
      </nav>
      <div className="panel-tab-body">
        {tab === "tools" && <ToolsPanel conversationId={conversationId} onEvent={onEvent} onConfirmation={onConfirmation} />}
        {tab === "memory" && <MemoryStatus />}
        {tab === "computer" && <ComputerUsePanel onEvent={onEvent} />}
        {tab === "activity" && <TimelinePanel events={events} />}
      </div>
    </aside>
  );
}
