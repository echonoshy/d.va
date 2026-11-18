import { spawn } from "node:child_process";
import { randomBytes } from "node:crypto";
import { createInterface } from "node:readline";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import { request } from "node:http";
import { pipeline } from "node:stream/promises";

const root = fileURLToPath(new URL("../", import.meta.url));
const secret = randomBytes(32).toString("hex");
let startup;
let child;

function worker() {
  if (startup) return startup;
  const python =
    process.env.DVA_PYTHON ||
    join(
      root,
      ".venv",
      process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
    );
  startup = new Promise((resolve, reject) => {
    const proc = spawn(python, ["-u", "-m", "modules.studio.service"], {
      cwd: root,
      env: {
        ...process.env,
        DVA_WORKER_TOKEN: secret,
        PYTORCH_ENABLE_MPS_FALLBACK: "1",
      },
      stdio: ["ignore", "pipe", "inherit"],
    });
    child = proc;
    const timer = setTimeout(() => {
      proc.kill();
      reject(new Error("模型服务启动超时，请查看服务日志。"));
    }, 150000);
    const lines = createInterface({ input: proc.stdout });
    lines.on("line", (line) => {
      const ready = /^DVA_READY (\d+)$/.exec(line);
      if (ready) {
        clearTimeout(timer);
        resolve("http://127.0.0.1:" + ready[1]);
      } else console.log(line);
    });
    const stopped = () => {
      clearTimeout(timer);
      if (child === proc) {
        child = undefined;
        startup = undefined;
      }
      reject(
        new Error(
          "语音工作台服务无法启动，请先在项目目录运行 uv sync --frozen，然后重试。",
        ),
      );
    };
    proc.once("error", stopped);
    proc.once("exit", stopped);
  });
  return startup;
}

export function stopStudio() {
  child?.kill();
}

export async function serveStudio(req, res, path, readBody) {
  const method = req.method;
  const route = path.slice("/api/studio".length);
  if (!(
    (method === "GET" &&
      (route === "/schema" ||
        /^\/speakers\/[\w-]+$/.test(route) ||
        /^\/files\/[\w-]+\/[\w-]+$/.test(route))) ||
    (method === "POST" &&
      /^\/(run\/[\w-]+\/\d+|upload\/[\w-]+|speakers\/[\w-]+)$/.test(route))
  )) {
    res.writeHead(404);
    res.end();
    return;
  }
  const payload =
    method === "POST"
      ? await readBody(
          req,
          route.startsWith("/upload/")
            ? 32 * 1024 ** 2
            : route.startsWith("/speakers/")
              ? 16 * 1024 ** 2
              : 1024 ** 2,
        )
      : undefined;
  const url = new URL(route, await worker());
  if (route.startsWith("/upload/"))
    url.searchParams.set(
      "name",
      new URL(req.url, "http://localhost").searchParams.get("name") || "",
    );
  await relay(
    req,
    res,
    url,
    payload,
    route.startsWith("/upload/")
      ? "application/octet-stream"
      : "application/json",
  );
}

async function relay(req, res, url, payload, contentType) {
  const proxy = request(url, {
    method: req.method,
    headers: { "x-dva-worker": secret, "content-type": contentType },
  });
  const reply = new Promise((resolve, reject) => {
    proxy.once("response", resolve);
    proxy.once("error", reject);
  });
  const cancel = () => proxy.destroy();
  res.once("close", cancel);
  try {
    proxy.end(payload);
    const response = await reply;
    res.statusCode = response.statusCode;
    res.setHeader("Cache-Control", "no-store");
    for (const h of ["content-type", "content-disposition", "content-length"]) {
      if (response.headers[h]) res.setHeader(h, response.headers[h]);
    }
    await pipeline(response, res);
  } finally {
    res.off("close", cancel);
    proxy.destroy();
  }
}

export async function serveLegacy(req, res, readBody) {
  const path = new URL(req.url, "http://localhost");
  const url = new URL(await worker());
  url.pathname = "/legacy" + path.pathname;
  url.search = path.search;
  const data = ["POST", "PUT", "PATCH"].includes(req.method)
    ? await readBody(req, 32 * 1024 ** 2)
    : undefined;
  await relay(
    req,
    res,
    url,
    data,
    req.headers["content-type"] || "application/json",
  );
}
