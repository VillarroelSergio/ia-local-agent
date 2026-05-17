"""Agente IA local por consola.

Conecta LM Studio mediante la API compatible con OpenAI, mantiene el historial
de conversacion, gestiona streaming, tool calling con confirmacion del usuario
y memoria persistente.
"""

import json

from openai import OpenAI

try:
    from memory import forget, format_memories_for_prompt, load_memories, remember
    from tools import TOOL_SCHEMAS, run_tool
except ModuleNotFoundError:
    from src.memory import forget, format_memories_for_prompt, load_memories, remember
    from src.tools import TOOL_SCHEMAS, run_tool

MODEL = "qwen/qwen3.5-9b"

client = OpenAI(
    base_url="http://127.0.0.1:1234/v1",
    api_key="lm-studio"
)

def build_system_prompt():
    """Construye el prompt del sistema incluyendo la memoria persistente."""
    return f"""
        Eres un asistente IA local integrado en Windows.
        Ayudas al usuario con tareas diarias y desarrollo.
        Puedes pedir herramientas cuando sean utiles, pero el usuario
        siempre debe confirmar antes de ejecutarlas.

        Memoria persistente del usuario:
        {format_memories_for_prompt()}
        """


messages = [
    {
        "role": "system",
        "content": build_system_prompt()
    }
]


def refresh_system_prompt():
    """Actualiza el mensaje system con las memorias guardadas mas recientes."""
    messages[0]["content"] = build_system_prompt()


def stream_response(use_tools=True):
    """Solicita una respuesta al modelo y la imprime en streaming.

    Cuando use_tools es True, el modelo puede devolver tool calls. En streaming
    esos tool calls llegan fragmentados, asi que se reconstruyen por indice.
    """
    request = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.7,
        "stream": True,
    }

    if use_tools:
        request["tools"] = TOOL_SCHEMAS
        request["tool_choice"] = "auto"

    stream = client.chat.completions.create(**request)

    assistant_message = ""
    tool_calls = {}

    print("\nIA: ", end="", flush=True)

    for chunk in stream:
        delta = chunk.choices[0].delta

        if delta.content:
            print(delta.content, end="", flush=True)
            assistant_message += delta.content

        if delta.tool_calls:
            for tool_call in delta.tool_calls:
                index = tool_call.index

                if index not in tool_calls:
                    tool_calls[index] = {
                        "id": "",
                        "type": "function",
                        "function": {
                            "name": "",
                            "arguments": "",
                        },
                    }

                if tool_call.id:
                    tool_calls[index]["id"] += tool_call.id

                if tool_call.function:
                    if tool_call.function.name:
                        tool_calls[index]["function"]["name"] += tool_call.function.name

                    if tool_call.function.arguments:
                        tool_calls[index]["function"]["arguments"] += tool_call.function.arguments

    normalized_tool_calls = []

    for index, tool_call in tool_calls.items():
        if not tool_call["id"]:
            tool_call["id"] = f"call_{index}"

        normalized_tool_calls.append(tool_call)

    print()
    return assistant_message, normalized_tool_calls


def parse_tool_arguments(tool_call):
    """Convierte los argumentos JSON de una tool call en un diccionario."""
    raw_arguments = tool_call["function"].get("arguments") or "{}"

    try:
        arguments = json.loads(raw_arguments)
    except json.JSONDecodeError:
        return {
            "_error": "No se pudieron leer los argumentos JSON de la tool.",
            "_raw_arguments": raw_arguments,
        }

    if not isinstance(arguments, dict):
        return {
            "_error": "Los argumentos de la tool deben ser un objeto JSON.",
            "_raw_arguments": raw_arguments,
        }

    return arguments


def confirm_tool(tool_name, arguments):
    """Pide confirmacion antes de ejecutar una tool solicitada por el modelo."""
    print(f"\nEl modelo quiere ejecutar '{tool_name}' con argumentos:")
    print(json.dumps(arguments, indent=2, ensure_ascii=False))
    answer = input("Confirmar? (s/n): ")
    return answer.strip().lower() in ["s", "si", "y", "yes"]


def run_confirmed_tool_call(tool_call):
    """Valida, confirma y ejecuta una tool call del modelo."""
    tool_name = tool_call["function"]["name"]
    arguments = parse_tool_arguments(tool_call)

    if "_error" in arguments:
        return arguments

    if not confirm_tool(tool_name, arguments):
        return "Tool cancelada por el usuario."

    return run_tool(tool_name, arguments)


def handle_memory_command(user_input):
    """Gestiona comandos manuales de memoria.

    Devuelve True si el input fue un comando de memoria y ya quedo resuelto.
    """
    if user_input.startswith("/remember "):
        content = user_input.removeprefix("/remember ").strip()
        memory = remember(content)
        refresh_system_prompt()
        print("\nMemoria:", memory)
        return True

    if user_input == "/memories":
        memories = load_memories()
        print("\nMemorias:")

        if not memories:
            print("No hay memoria persistente guardada todavia.")
            return True

        for memory in memories:
            print(f"- [{memory.get('id')}] {memory.get('content')}")

        return True

    if user_input.startswith("/forget "):
        memory_id = user_input.removeprefix("/forget ").strip()
        result = forget(memory_id)
        refresh_system_prompt()
        print("\nMemoria:", result)
        return True

    return False


def chat_once():
    """Procesa una interaccion completa de chat.

    Si el modelo pide tools, se ejecutan con confirmacion y despues se hace una
    segunda llamada al modelo para que responda con el resultado.
    """
    refresh_system_prompt()
    assistant_message, tool_calls = stream_response(use_tools=True)

    if not tool_calls:
        messages.append({
            "role": "assistant",
            "content": assistant_message
        })
        return

    messages.append({
        "role": "assistant",
        "content": assistant_message or None,
        "tool_calls": tool_calls,
    })

    for tool_call in tool_calls:
        result = run_confirmed_tool_call(tool_call)
        print("\nTool:", result)

        messages.append({
            "role": "tool",
            "tool_call_id": tool_call["id"],
            "name": tool_call["function"]["name"],
            "content": json.dumps(result, ensure_ascii=False),
        })

    final_message, _ = stream_response(use_tools=False)

    messages.append({
        "role": "assistant",
        "content": final_message
    })


def main():
    """Bucle principal de consola del agente."""
    print("Agente IA local iniciado. Escribe 'salir' para terminar.")
    print("Tools manuales: /tool notepad, /tool calc, /tool sistema")
    print("Memoria: /remember texto, /memories, /forget id")

    while True:
        user_input = input("\nTu: ").strip()

        if user_input.lower() == "salir":
            break

        if not user_input:
            continue

        if handle_memory_command(user_input):
            continue

        if user_input.startswith("/tool "):
            tool_request = user_input.removeprefix("/tool ").strip()
            tool_name, _, raw_arguments = tool_request.partition(" ")

            try:
                arguments = json.loads(raw_arguments) if raw_arguments else {}
            except json.JSONDecodeError as error:
                print("\nTool: JSON invalido en los argumentos:", error)
                continue

            result = run_tool(tool_name.lower(), arguments)
            print("\nTool:", result)
            continue

        history_length = len(messages)
        messages.append({
            "role": "user",
            "content": user_input
        })

        try:
            chat_once()
        except Exception as error:
            del messages[history_length:]
            print("\nError al conectar con LM Studio:", error)
            print("Comprueba que el server esta activo y que hay un modelo cargado.")
            continue


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAgente detenido.")
