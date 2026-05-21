import { describe, expect, it, vi } from "vitest";
import { ApiClient } from "./apiClient";

describe("ApiClient", () => {
  it("builds authenticated conversation requests", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [{ id: "c1", title: "Test", message_count: 0 }],
    });
    vi.stubGlobal("fetch", fetchMock);
    const client = new ApiClient("http://api.local", "token");

    const result = await client.listConversations();

    expect(result[0].id).toBe("c1");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.local/api/conversations",
      expect.objectContaining({
        headers: expect.any(Headers),
      }),
    );
    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get("x-api-key")).toBe("token");
  });
});
