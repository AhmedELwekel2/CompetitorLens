import http from "http";

const FLASK_HOST = process.env.AI_API_HOST || "ai-api";
const FLASK_PORT = parseInt(process.env.AI_API_PORT || "5000", 10);

// 10-minute timeout for long-running AI analysis requests
const UPSTREAM_TIMEOUT_MS = 10 * 60 * 1000;

/**
 * Stream a POST request to the Flask API using Node's http module
 * (avoids undici/fetch internal timeouts that break long-running SSE).
 */
function streamPost(
  path: string,
  body: string
): Promise<{
  status: number;
  headers: Headers;
  body: ReadableStream<Uint8Array>;
}> {
  return new Promise((resolve, reject) => {
    const req = http.request(
      {
        hostname: FLASK_HOST,
        port: FLASK_PORT,
        path,
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
          "Content-Length": Buffer.byteLength(body),
        },
        timeout: UPSTREAM_TIMEOUT_MS,
      },
      (res) => {
        const headers = new Headers();
        for (const [key, value] of Object.entries(res.headers)) {
          if (value) {
            headers.set(key, Array.isArray(value) ? value.join(", ") : value);
          }
        }

        const stream = new ReadableStream<Uint8Array>({
          start(controller) {
            res.on("data", (chunk: Buffer) =>
              controller.enqueue(new Uint8Array(chunk))
            );
            res.on("end", () => controller.close());
            res.on("error", (err: Error) => controller.error(err));
          },
        });

        resolve({
          status: res.statusCode || 200,
          headers,
          body: stream,
        });
      }
    );

    req.on("error", (err: Error) => {
      console.error(`[AI Proxy] http.request error for ${path}:`, err.message);
      reject(err);
    });

    req.on("timeout", () => {
      req.destroy();
      reject(new Error("Upstream AI service timed out"));
    });

    req.write(body);
    req.end();
  });
}

/**
 * Simple GET proxy to the Flask API (for health checks, etc.)
 */
function proxyGet(
  path: string
): Promise<{ status: number; contentType: string; body: string }> {
  return new Promise((resolve, reject) => {
    const req = http.request(
      {
        hostname: FLASK_HOST,
        port: FLASK_PORT,
        path,
        method: "GET",
        headers: { Accept: "application/json" },
        timeout: 30_000,
      },
      (res) => {
        const chunks: Buffer[] = [];
        res.on("data", (chunk: Buffer) => chunks.push(chunk));
        res.on("end", () => {
          resolve({
            status: res.statusCode || 200,
            contentType:
              res.headers["content-type"] || "application/json",
            body: Buffer.concat(chunks).toString("utf-8"),
          });
        });
        res.on("error", reject);
      }
    );
    req.on("error", reject);
    req.on("timeout", () => {
      req.destroy();
      reject(new Error("Upstream AI service timed out"));
    });
    req.end();
  });
}

// ── POST handler (SSE streaming) ──────────────────────────────────────────────

export async function POST(
  request: Request,
  ctx: RouteContext<"/ai/[...path]">
) {
  const { path: segments } = await ctx.params;
  const pathname = "/" + (segments as string[]).join("/");
  const flaskPath = `/ai${pathname}`;

  const body = await request.text();

  try {
    const upstream = await streamPost(flaskPath, body);

    // If the upstream returned an error status, forward it as JSON
    if (upstream.status >= 400) {
      const reader = upstream.body.getReader();
      const chunks: Uint8Array[] = [];
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        if (value) chunks.push(value);
      }
      const text = Buffer.concat(chunks).toString("utf-8");
      return new Response(text, {
        status: upstream.status,
        headers: { "Content-Type": "application/json" },
      });
    }

    // Stream the SSE response back to the client
    const responseHeaders = new Headers();
    responseHeaders.set("Content-Type", "text/event-stream");
    responseHeaders.set("Cache-Control", "no-cache, no-transform");
    responseHeaders.set("Connection", "keep-alive");
    responseHeaders.set("X-Accel-Buffering", "no");

    return new Response(upstream.body, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Failed to reach AI service";
    console.error(`[AI Proxy] POST ${flaskPath} failed:`, message);
    return new Response(JSON.stringify({ error: message }), {
      status: 502,
      headers: { "Content-Type": "application/json" },
    });
  }
}

// ── GET handler (health checks, etc.) ─────────────────────────────────────────

export async function GET(
  _request: Request,
  ctx: RouteContext<"/ai/[...path]">
) {
  const { path: segments } = await ctx.params;
  const pathname = "/" + (segments as string[]).join("/");
  const flaskPath = `/ai${pathname}`;

  try {
    const upstream = await proxyGet(flaskPath);
    return new Response(upstream.body, {
      status: upstream.status,
      headers: { "Content-Type": upstream.contentType },
    });
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Failed to reach AI service";
    console.error(`[AI Proxy] GET ${flaskPath} failed:`, message);
    return new Response(JSON.stringify({ error: message }), {
      status: 502,
      headers: { "Content-Type": "application/json" },
    });
  }
}