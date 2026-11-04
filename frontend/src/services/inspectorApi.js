/** Same-origin API by default; hosts may supply their own fetch adapter. */
export function createInspectorApi(baseUrl, fetchImpl = globalThis.fetch) {
  const base = baseUrl.replace(/\/+$/, "") + "/";
  const url = (path) => base + path.replace(/^\/+/, "");
  async function request(path, options = {}) {
    const response = await fetchImpl(url(path), {
      credentials: "same-origin",
      ...options,
    });
    let body;
    try {
      body = await response.json();
    } catch {
      throw new Error(
        "The request could not finish (" +
          response.status +
          "). Check file limits and try again.",
      );
    }
    if (!response.ok)
      throw new Error(
        body.error || "Request failed (" + response.status + ").",
      );
    return body;
  }
  return { url, request };
}
