import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MessageBubble } from "./MessageBubble";

describe("MessageBubble", () => {
  it("renders user and assistant messages", () => {
    render(
      <>
        <MessageBubble message={{ role: "user", content: "Hola" }} />
        <MessageBubble message={{ role: "assistant", content: "**Buenas**" }} />
      </>,
    );

    expect(screen.getByText("Hola")).toBeInTheDocument();
    expect(screen.getByText("Buenas")).toBeInTheDocument();
  });
});
