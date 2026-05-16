from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio"
)

messages = [
    {
        "role": "system",
        "content": """
        Eres un asistente IA local para Windows.
        Ayudas al usuario con tareas diarias y desarrollo.
        """
    }
]

while True:
    user_input = input("Tu: ")

    messages.append({
        "role": "user",
        "content": user_input
    })

    response = client.chat.completions.create(
        model="qwen",
        messages=messages,
        temperature=0.7
    )

    assistant_message = response.choices[0].message.content

    print("\nIA:", assistant_message)

    messages.append({
        "role": "assistant",
        "content": assistant_message
    })