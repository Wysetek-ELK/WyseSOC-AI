import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

test("Sentinel UI: removes hardcoded 1024 max_tokens and renders required lifecycle warnings", () => {
  const page = fs.readFileSync(path.resolve("src/app/soc-chatbot/page.tsx"), "utf-8");
  assert.doesNotMatch(page, /max_tokens:\s*1024/, "Must not hardcode max_tokens: 1024 in Sentinel chat");
  assert.match(page, /Response incomplete — generation limit reached\./);
  assert.match(page, /Response interrupted — the investigation may be incomplete\./);
  assert.match(
    page,
    /The request exceeds the available model context\. Reduce the input or divide the investigation into smaller stages\./
  );
  assert.match(page, /Continue Response/);
  assert.match(page, /<details[\s\S]*Technical Details/);
  assert.match(page, /handleContinueResponse/);
  assert.match(page, /listChatConversations/);
});

test("Sentinel API Client & Next.js Proxy: enforces stream termination integrity and 600s timeout", () => {
  const apiContent = fs.readFileSync(path.resolve("src/lib/api.ts"), "utf-8");
  assert.match(apiContent, /consumeChatSseResponse/);
  assert.match(apiContent, /stream_closed_without_done/);
  assert.match(apiContent, /continueChatMessage/);
  assert.match(apiContent, /listChatConversations/);
  assert.match(apiContent, /getChatConversation/);
  assert.match(apiContent, /600_000/);

  const nextCfg = fs.readFileSync(path.resolve("next.config.ts"), "utf-8");
  assert.match(nextCfg, /proxyTimeout:\s*600_000/);
});
