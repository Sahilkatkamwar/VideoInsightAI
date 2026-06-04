import type { Source } from "./types";

export interface StreamEvent {
  type: "token" | "sources" | "done" | "error";
  content?: string;
  sources?: Source[];
  message?: string;
}

export async function* readSSEStream(
  response: Response
): AsyncGenerator<StreamEvent> {
  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const event = JSON.parse(line.slice(6)) as StreamEvent;
          yield event;
          if (event.type === "done" || event.type === "error") return;
        } catch {
          // Malformed JSON line — skip
        }
      }
    }
  }
}
