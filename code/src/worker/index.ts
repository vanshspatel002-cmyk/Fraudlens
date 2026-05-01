import { Hono } from "hono";

type WorkerEnv = {
  API_BASE_URL?: string;
};

const app = new Hono<{ Bindings: WorkerEnv }>();

app.all("/api/*", async (c) => {
  const apiBaseUrl = c.env.API_BASE_URL?.replace(/\/$/, "");

  if (!apiBaseUrl) {
    return c.json(
      {
        error:
          "API_BASE_URL is not configured for this deployment. Point it at the Flask backend.",
      },
      502
    );
  }

  const incomingUrl = new URL(c.req.url);
  const targetUrl = `${apiBaseUrl}${incomingUrl.pathname}${incomingUrl.search}`;
  const proxiedRequest = new Request(targetUrl, c.req.raw);

  return fetch(proxiedRequest);
});

export default app;
