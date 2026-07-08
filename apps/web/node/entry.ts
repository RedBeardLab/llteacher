import { serve } from "@hono/node-server";
import { createReadStream } from "node:fs";
import { access, stat } from "node:fs/promises";
import { extname, isAbsolute, join, normalize, relative, resolve } from "node:path";
import { Readable } from "node:stream";
import app from "../src/server/index";

const port = Number.parseInt(process.env.PORT ?? "8080", 10);
const webRoot = resolve(process.env.WEB_ASSETS_DIR ?? "apps/web/dist/client");
const adminRoot = resolve(process.env.ADMIN_ASSETS_DIR ?? "apps/admin/dist/client");

const contentTypes: Record<string, string> = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};

async function existingFile(root: string, requestedPath: string): Promise<string | undefined> {
  const safePath = normalize(requestedPath).replace(/^(\.\.(\/|\\|$))+/, "");
  const candidate = resolve(root, safePath);
  const relativeCandidate = relative(root, candidate);
  if (relativeCandidate.startsWith("..") || isAbsolute(relativeCandidate)) return undefined;
  try {
    await access(candidate);
    return (await stat(candidate)).isFile() ? candidate : undefined;
  } catch {
    return undefined;
  }
}

async function staticResponse(request: Request): Promise<Response> {
  const pathname = new URL(request.url).pathname;
  const isAdmin = pathname === "/instructor" || pathname.startsWith("/instructor/");
  const root = isAdmin ? adminRoot : webRoot;
  const relativePath = isAdmin
    ? pathname.replace(/^\/instructor\/?/, "")
    : pathname.replace(/^\//, "");
  const requestedFile = relativePath ? await existingFile(root, relativePath) : undefined;
  const file = requestedFile ?? join(root, "index.html");

  try {
    await access(file);
    const nodeStream = createReadStream(file);
    return new Response(Readable.toWeb(nodeStream) as ReadableStream, {
      headers: {
        "content-type": contentTypes[extname(file)] ?? "application/octet-stream",
        "x-content-type-options": "nosniff",
      },
    });
  } catch {
    return new Response("Not Found", { status: 404 });
  }
}

const assets = { fetch: staticResponse };

serve(
  {
    port,
    fetch: (request) => {
      const pathname = new URL(request.url).pathname;
      if (pathname === "/health") {
        return Response.json({ status: "ok" });
      }
      return app.fetch(request, {
        DATABASE_URL: process.env.DATABASE_URL ?? "",
        WORKOS_API_KEY: process.env.WORKOS_API_KEY ?? "",
        WORKOS_CLIENT_ID: process.env.WORKOS_CLIENT_ID ?? "",
        OPENROUTER_API_KEY: process.env.OPENROUTER_API_KEY ?? "",
        ASSETS: assets,
      } as Env);
    },
  },
  ({ port: listeningPort }) => {
    console.log(`LLTeacher AWS server listening on port ${listeningPort}`);
  },
);
