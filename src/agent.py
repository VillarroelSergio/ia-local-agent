import json

from openai import OpenAI

try:
    from tools import TOOL_SCHEMAS, run_tool
except ModuleNotFoundError:
    from src.tools import TOOL_SCHEMAS, run_tool

MODEL = "qwen/qwen3.5-9b"

client = OpenAI(
    base_url="http://127.0.0.1:1234/v1",
    api_key="lm-studio"
)

messages = [
    {
        "role": "system",
        "content": """
        Eres un asistente IA local integrado en Windows.
        Ayudas al usuario con tareas diarias y desarrollo.
        Puedes pedir herramientas cuando sean utiles, pero el usuario
        siempre debe confirmar antes de ejecutarlas.
        """
    }
]


def stream_response(use_tools=True):
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
    print(f"\nEl modelo quiere ejecutar '{tool_name}' con argumentos:")
    print(json.dumps(arguments, indent=2, ensure_ascii=False))
    answer = input("Confirmar? (s/n): ")
    return answer.strip().lower() in ["s", "si", "y", "yes"]


def run_confirmed_tool_call(tool_call):
    tool_name = tool_call["function"]["name"]
    arguments = parse_tool_arguments(tool_call)

    if "_error" in arguments:
        return arguments

    if not confirm_tool(tool_name, arguments):
        return "Tool cancelada por el usuario."

    return run_tool(tool_name, arguments)


def chat_once():
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
    print("Agente IA local iniciado. Escribe 'salir' para terminar.")
    print("Tools manuales: /tool notepad, /tool calc, /tool sistema")

    while True:
        user_input = input("\nTu: ").strip()

        if user_input.lower() == "salir":
            break

        if not user_input:
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
