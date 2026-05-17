"""Factory de grafo LangGraph para el agente local.

Este modulo es deliberadamente ligero: prepara la arquitectura sin obligar al
CLI actual a migrar en bloque. Los nodos LLM concretos pueden inyectarse desde
LocalAgent cuando se quiera activar el runtime graph-first.
"""

from __future__ import annotations

try:
    from langgraph.graph import END, StateGraph
except ImportError:  # pragma: no cover - permite importar sin langgraph.
    END = None
    StateGraph = None

from .nodes import finalize_with_summary, initialize_state, plan_from_user_input
from .state import AgentState


def build_minimal_agent_graph():
    """Crea un grafo base: init -> planner -> finalizer.

    Es el esqueleto sobre el que se conectan retrieve_memory, agent_llm,
    execute_tools y reflection.
    """
    if StateGraph is None:
        raise RuntimeError("langgraph no esta instalado en el entorno actual.")

    graph = StateGraph(AgentState)
    graph.add_node("initialize", initialize_state)
    graph.add_node("planner", plan_from_user_input)
    graph.add_node("finalize", finalize_with_summary)

    graph.set_entry_point("initialize")
    graph.add_edge("initialize", "planner")
    graph.add_edge("planner", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()
