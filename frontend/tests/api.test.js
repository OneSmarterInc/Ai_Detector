import test from "node:test";
import assert from "node:assert/strict";
import { createInspectorApi } from "../src/services/inspectorApi.js";

test("host path and fetch adapter are used for every request", async () => {
  let captured;
  const api = createInspectorApi(
    "/host/tools/inspector",
    async (url, options) => {
      captured = { url, options };
      return { ok: true, json: async () => ({ ready: true }) };
    },
  );
  assert.deepEqual(await api.request("/info/"), { ready: true });
  assert.equal(captured.url, "/host/tools/inspector/info/");
  assert.equal(captured.options.credentials, "same-origin");
  assert.equal(
    api.url("jobs/123/report/"),
    "/host/tools/inspector/jobs/123/report/",
  );
});

test("server errors remain readable", async () => {
  const api = createInspectorApi("/tools/", async () => ({
    ok: false,
    status: 400,
    json: async () => ({ error: "Choose a file." }),
  }));
  await assert.rejects(api.request("jobs/"), /Choose a file/);
});

test("non-JSON errors do not crash the response parser", async () => {
  const api = createInspectorApi("/tools/", async () => ({
    status: 502,
    json: async () => {
      throw new Error("HTML");
    },
  }));
  await assert.rejects(api.request("jobs/"), /502/);
});
