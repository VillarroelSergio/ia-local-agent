import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { apiClient } from "../../services/apiClient";

/** Presenta el estado de memoria/RAG y permite reconstruir o buscar contenido indexado. */
export function MemoryStatus() {
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [ragStats, setRagStats] = useState<Record<string, unknown> | null>(null);
  const [query, setQuery] = useState("");
  const [ragPath, setRagPath] = useState("");
  const [ragProject, setRagProject] = useState("default");
  const [ragResult, setRagResult] = useState<Record<string, unknown> | null>(null);
  const [ragDocuments, setRagDocuments] = useState<Record<string, unknown>[]>([]);
  const [search, setSearch] = useState<unknown[]>([]);

  /** Carga las estadisticas actuales de memoria desde el backend. */
  async function load() {
    const [memory, rag, docs] = await Promise.all([
      apiClient.memoryStats(),
      apiClient.ragStats().catch(() => null),
      apiClient.ragDocuments().catch(() => null),
    ]);
    setStats(memory);
    setRagStats(rag);
    setRagDocuments(docs?.documents ?? []);
  }

  useEffect(() => {
    load().catch(() => setStats(null));
  }, []);

  return (
    <section className="memory-card">
      <div className="panel-heading">
        <h2>Memoria/RAG</h2>
        <button className="mini-button" title="Refrescar" onClick={load}>
          <RefreshCw size={14} />
        </button>
      </div>
      <div className="memory-summary">
        <div>
          <strong>{stats ? "Activa" : "Sin conexion"}</strong>
          <span>Estado</span>
        </div>
        <div>
          <strong>{String(stats?.conversation_messages ?? stats?.total ?? "-")}</strong>
          <span>Mensajes</span>
        </div>
        <div>
          <strong>{String(stats?.long_term_enabled ?? stats?.enabled ?? "-")}</strong>
          <span>Largo plazo</span>
        </div>
        <div>
          <strong>{String(stats?.embedding ?? stats?.embedding_provider ?? "-")}</strong>
          <span>Embedding</span>
        </div>
      </div>
      <div className="memory-actions">
        <button className="secondary-action" onClick={() => apiClient.rebuildMemory().then(setStats)}>
          Rebuild
        </button>
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar memoria" />
        <button className="secondary-action" onClick={() => query.trim() && apiClient.searchMemory(query).then(setSearch)}>
          Buscar
        </button>
      </div>
      <div className="rag-manager">
        <h3>Documentos RAG</h3>
        <div className="memory-summary">
          <div>
            <strong>{String(ragStats?.documents ?? ragStats?.total_documents ?? "-")}</strong>
            <span>Documentos</span>
          </div>
          <div>
            <strong>{String(ragStats?.chunks ?? ragStats?.total_chunks ?? "-")}</strong>
            <span>Chunks</span>
          </div>
        </div>
        <label>
          Ruta
          <input value={ragPath} onChange={(event) => setRagPath(event.target.value)} placeholder="D:\\docs o README.md" />
        </label>
        <label>
          Proyecto
          <input value={ragProject} onChange={(event) => setRagProject(event.target.value)} />
        </label>
        <button
          className="secondary-action"
          onClick={() => ragPath.trim() && apiClient.indexRag(ragPath, ragProject).then((result) => { setRagResult(result); load(); })}
        >
          Indexar
        </button>
        {ragResult && <pre>{JSON.stringify(ragResult, null, 2)}</pre>}
        {ragDocuments.length > 0 && (
          <div className="memory-results">
            {ragDocuments.slice(0, 20).map((doc) => (
              <div key={String(doc.source_path)}>
                <strong>{String(doc.source_path)}</strong>
                <span> v{String(doc.version ?? "-")} - {String(doc.indexed_at ?? "sin fecha")}</span>
              </div>
            ))}
          </div>
        )}
      </div>
      {search.length > 0 && (
        <div className="memory-results">
          {search.slice(0, 5).map((item, index) => (
            <div key={index}>{summarizeMemoryResult(item)}</div>
          ))}
        </div>
      )}
    </section>
  );
}

/** Resume resultados heterogeneos de memoria en una cadena corta para la lista. */
function summarizeMemoryResult(item: unknown) {
  if (!item || typeof item !== "object") return String(item);
  const value = item as Record<string, unknown>;
  return String(value.content ?? value.text ?? value.id ?? "Resultado de memoria");
}
