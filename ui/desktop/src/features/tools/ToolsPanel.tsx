import { Play, RefreshCw, Search } from "lucide-react";
import { useEffect, useState } from "react";
import type { ConfirmationPayload, ToolExecuteResponse, ToolInfo } from "../../types/api";
import { apiClient } from "../../services/apiClient";

interface Props {
  conversationId?: string;
  onEvent: (event: Record<string, unknown>) => void;
  onConfirmation: (payload: ConfirmationPayload) => void;
}

export function ToolsPanel({ conversationId, onEvent, onConfirmation }: Props) {
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [selected, setSelected] = useState<ToolInfo | null>(null);
  const [args, setArgs] = useState<Record<string, string>>({});
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<ToolExecuteResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const items = await apiClient.listTools();
    setTools(items);
    setSelected((current) => current ?? items[0] ?? null);
  }

  useEffect(() => {
    load().catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  async function execute() {
    if (!selected) return;
    setError(null);
    const parsed = buildArguments(selected, args);
    const response = await apiClient.executeTool(selected.name, parsed, conversationId, false);
    setResult(response);
    onEvent({ type: response.ok ? "tool.completed" : "tool.failed", data: response, timestamp: new Date().toISOString() });
    if (response.requires_user_action) {
      onConfirmation({
        tool_name: selected.name,
        arguments: parsed,
        conversation_id: conversationId,
        risk_level: response.risk_level ?? selected.risk_level,
        reason: response.error ? JSON.stringify(response.error) : null,
        source: "tools",
      });
    }
  }

  const visibleTools = tools.filter((tool) => {
    const term = query.trim().toLowerCase();
    if (!term) return true;
    return `${tool.name} ${tool.description} ${tool.category}`.toLowerCase().includes(term);
  });
  const grouped = groupTools(visibleTools);
  const fields = selected ? getArgumentFields(selected) : [];

  return (
    <section className="tools-panel">
      <div className="panel-heading">
        <h2>Tools</h2>
        <button className="mini-button" title="Refrescar" onClick={() => load()}>
          <RefreshCw size={14} />
        </button>
      </div>
      {error && <div className="error-box">{error}</div>}
      <label className="search-field">
        <Search size={15} />
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar tool" />
      </label>
      <div className="tool-list">
        {Object.entries(grouped).map(([category, items]) => (
          <div className="tool-group" key={category}>
            <h3>{category}</h3>
            {items.map((tool) => (
              <button key={tool.name} className={selected?.name === tool.name ? "selected" : ""} onClick={() => setSelected(tool)}>
                <span>{humanizeToolName(tool.name)}</span>
                <small>{tool.requires_confirmation ? "Pide confirmacion" : "Uso directo"}</small>
              </button>
            ))}
          </div>
        ))}
      </div>
      {selected && (
        <div className="tool-detail">
          <h3>{humanizeToolName(selected.name)}</h3>
          <p>{selected.description}</p>
          <div className="tool-meta">
            <span>{labelCategory(selected.category)}</span>
            <span>{selected.requires_confirmation ? "Pide confirmacion" : "Uso directo"}</span>
          </div>
          {fields.length > 0 && (
            <div className="tool-arguments">
              {fields.map((field) => (
                <label key={field.name}>
                  {field.label}
                  <input
                    value={args[field.name] ?? ""}
                    placeholder={field.placeholder}
                    onChange={(event) => setArgs((current) => ({ ...current, [field.name]: event.target.value }))}
                  />
                </label>
              ))}
            </div>
          )}
          <button className="primary-action" onClick={execute}>
            <Play size={15} />
            Ejecutar
          </button>
          {result && <div className={result.ok ? "result-card success" : "result-card error"}>{result.ok ? "Tool ejecutada." : "La tool fallo."}</div>}
        </div>
      )}
    </section>
  );
}

function getArgumentFields(tool: ToolInfo) {
  const functionSchema = tool.schema?.function as { parameters?: { properties?: Record<string, { type?: string; description?: string }> } } | undefined;
  const properties = functionSchema?.parameters?.properties ?? {};
  return Object.entries(properties)
    .filter(([name]) => !name.startsWith("_"))
    .slice(0, 6)
    .map(([name, schema]) => ({
      name,
      label: humanizeToolName(name),
      placeholder: schema.description ?? schema.type ?? "Valor",
    }));
}

function buildArguments(tool: ToolInfo, values: Record<string, string>) {
  const fields = getArgumentFields(tool);
  return fields.reduce<Record<string, unknown>>((payload, field) => {
    const value = values[field.name]?.trim();
    if (value) payload[field.name] = value;
    return payload;
  }, {});
}

function groupTools(tools: ToolInfo[]) {
  return tools.reduce<Record<string, ToolInfo[]>>((groups, tool) => {
    const category = labelCategory(tool.category);
    groups[category] = [...(groups[category] ?? []), tool];
    return groups;
  }, {});
}

function labelCategory(category: string) {
  const normalized = category.toLowerCase();
  if (normalized.includes("window")) return "Ventanas";
  if (normalized.includes("screen") || normalized.includes("ocr") || normalized.includes("vision")) return "Pantalla";
  if (normalized.includes("file")) return "Archivos";
  if (normalized.includes("app")) return "Aplicaciones";
  if (normalized.includes("clipboard")) return "Portapapeles";
  if (normalized.includes("rag") || normalized.includes("memory")) return "Memoria";
  if (normalized.includes("system") || normalized.includes("powershell")) return "Sistema";
  return humanizeToolName(category);
}

function humanizeToolName(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
