const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "content-length",
  "host",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

function getBackendBaseUrl() {
  const rawUrl =
    process.env.BACKEND_API_URL ||
    process.env.RENDER_BACKEND_URL ||
    process.env.API_BASE_URL ||
    process.env.VITE_API_BASE_URL ||
    process.env.VITE_API_URL ||
    "";

  const baseUrl = rawUrl.trim().replace(/\/$/, "");

  return baseUrl.endsWith("/api") ? baseUrl.slice(0, -4) : baseUrl;
}

function copyRequestHeaders(headers) {
  const copied = {};

  for (const [key, value] of Object.entries(headers)) {
    const lowerKey = key.toLowerCase();

    if (HOP_BY_HOP_HEADERS.has(lowerKey) || typeof value === "undefined") {
      continue;
    }

    copied[key] = Array.isArray(value) ? value.join(", ") : value;
  }

  return copied;
}

function copyResponseHeaders(response, res) {
  response.headers.forEach((value, key) => {
    if (!HOP_BY_HOP_HEADERS.has(key.toLowerCase())) {
      res.setHeader(key, value);
    }
  });
}

module.exports = async function handler(req, res) {
  const backendBaseUrl = getBackendBaseUrl();

  if (!backendBaseUrl) {
    res.status(500).json({
      error:
        "Backend API URL is not configured. Set BACKEND_API_URL on Vercel to your Render backend URL.",
    });
    return;
  }

  if (req.method === "OPTIONS") {
    res.status(204).end();
    return;
  }

  const incomingUrl = new URL(req.url || "/api", "https://fraudlens.local");
  const targetUrl = `${backendBaseUrl}${incomingUrl.pathname}${incomingUrl.search}`;
  const hasBody = !["GET", "HEAD"].includes(req.method || "GET");

  try {
    const fetchOptions = {
      method: req.method,
      headers: copyRequestHeaders(req.headers),
      redirect: "manual",
    };

    if (hasBody) {
      fetchOptions.body = req;
      fetchOptions.duplex = "half";
    }

    const response = await fetch(targetUrl, fetchOptions);
    const body = Buffer.from(await response.arrayBuffer());

    copyResponseHeaders(response, res);
    res.status(response.status).send(body);
  } catch (error) {
    res.status(502).json({
      error: "Could not reach the Render backend through the Vercel API proxy.",
      details: error instanceof Error ? error.message : String(error),
    });
  }
};
