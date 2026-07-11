import { createReadStream } from "node:fs";
import { realpath, stat } from "node:fs/promises";
import type { IncomingMessage, ServerResponse } from "node:http";
import { dirname, extname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig, type Plugin } from "vite";

const viewerRoot = dirname(fileURLToPath(import.meta.url));
const repositoryRoot = resolve(viewerRoot, "..");
const pdfRoot = resolve(repositoryRoot, "dist");
const generatedPublicRoot = resolve(repositoryRoot, "build/corpus-viewer/public");
const siteRoot = resolve(repositoryRoot, "build/corpus-viewer/site");
const pdfRoute = "/publication-pdfs/";

function end(response: ServerResponse, status: number, message: string): void {
  response.statusCode = status;
  response.setHeader("Content-Type", "text/plain; charset=utf-8");
  response.end(message);
}

function parseRange(
  header: string,
  size: number,
): { start: number; end: number } | null {
  const match = /^bytes=(\d*)-(\d*)$/.exec(header.trim());
  if (!match || (!match[1] && !match[2])) return null;

  if (!match[1]) {
    const suffix = Number(match[2]);
    if (!Number.isSafeInteger(suffix) || suffix <= 0) return null;
    return { start: Math.max(0, size - suffix), end: size - 1 };
  }

  const start = Number(match[1]);
  const requestedEnd = match[2] ? Number(match[2]) : size - 1;
  if (
    !Number.isSafeInteger(start) ||
    !Number.isSafeInteger(requestedEnd) ||
    start < 0 ||
    start >= size ||
    requestedEnd < start
  ) {
    return null;
  }
  return { start, end: Math.min(requestedEnd, size - 1) };
}

async function serveCanonicalPdf(
  request: IncomingMessage,
  response: ServerResponse,
): Promise<void> {
  if (request.method !== "GET" && request.method !== "HEAD") {
    response.setHeader("Allow", "GET, HEAD");
    end(response, 405, "Method not allowed");
    return;
  }
  const requestUrl = new URL(request.url ?? "/", "http://viewer.local");
  let filename: string;
  try {
    filename = decodeURIComponent(requestUrl.pathname.slice(pdfRoute.length));
  } catch {
    end(response, 400, "Malformed PDF path");
    return;
  }

  const candidate = resolve(pdfRoot, filename);
  if (
    !filename ||
    filename.includes("/") ||
    filename.includes("\\") ||
    extname(filename).toLowerCase() !== ".pdf" ||
    dirname(candidate) !== pdfRoot
  ) {
    end(response, 400, "Invalid PDF path");
    return;
  }

  let details;
  let realCandidate: string;
  try {
    const [realRoot, resolvedCandidate] = await Promise.all([
      realpath(pdfRoot),
      realpath(candidate),
    ]);
    if (dirname(resolvedCandidate) !== realRoot) {
      end(response, 400, "Invalid PDF path");
      return;
    }
    realCandidate = resolvedCandidate;
    details = await stat(realCandidate);
  } catch {
    end(response, 404, "PDF not found");
    return;
  }
  if (!details.isFile()) {
    end(response, 404, "PDF not found");
    return;
  }

  let start = 0;
  let finish = details.size - 1;
  const rangeHeader = request.headers.range;
  if (rangeHeader) {
    const range = parseRange(rangeHeader, details.size);
    if (!range) {
      response.statusCode = 416;
      response.setHeader("Content-Range", `bytes */${details.size}`);
      response.end();
      return;
    }
    ({ start, end: finish } = range);
    response.statusCode = 206;
    response.setHeader("Content-Range", `bytes ${start}-${finish}/${details.size}`);
  } else {
    response.statusCode = 200;
  }

  response.setHeader("Accept-Ranges", "bytes");
  response.setHeader("Cache-Control", "no-cache");
  response.setHeader("Content-Length", finish - start + 1);
  response.setHeader("Content-Type", "application/pdf");
  response.setHeader(
    "Content-Disposition",
    `inline; filename*=UTF-8''${encodeURIComponent(filename)}`,
  );
  if (request.method === "HEAD") {
    response.end();
    return;
  }
  createReadStream(realCandidate, { start, end: finish }).pipe(response);
}

function canonicalPdfDevServer(): Plugin {
  return {
    name: "general-corpus-canonical-pdfs",
    apply: "serve",
    configureServer(server) {
      server.middlewares.use((request, response, next) => {
        const pathname = new URL(
          request.url ?? "/",
          "http://viewer.local",
        ).pathname;
        if (!pathname.startsWith(pdfRoute)) {
          next();
          return;
        }
        void serveCanonicalPdf(request, response);
      });
    },
  };
}

export default defineConfig({
  base: "./",
  plugins: [react(), canonicalPdfDevServer()],
  publicDir: generatedPublicRoot,
  build: {
    outDir: siteRoot,
    emptyOutDir: true,
  },
  server: {
    fs: {
      allow: [viewerRoot, generatedPublicRoot],
    },
  },
});
