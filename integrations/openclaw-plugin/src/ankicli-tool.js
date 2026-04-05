import { spawn, spawnSync } from "node:child_process";
import path from "node:path";

const BACKEND_VALUES = new Set(["python-anki", "ankiconnect"]);

export function resolvePluginConfig(api) {
  const config = api.pluginConfig ?? {};
  const rawPath =
    typeof config.ankicliPath === "string" && config.ankicliPath.trim()
      ? config.ankicliPath.trim()
      : "ankicli";
  const ankicliPath =
    rawPath.includes(path.sep) || rawPath.startsWith(".") ? api.resolvePath(rawPath) : rawPath;
  const collectionPath =
    typeof config.collectionPath === "string" && config.collectionPath.trim()
      ? api.resolvePath(config.collectionPath.trim())
      : undefined;
  const backend =
    typeof config.backend === "string" && BACKEND_VALUES.has(config.backend.trim())
      ? config.backend.trim()
      : undefined;
  const ankiconnectUrl =
    typeof config.ankiconnectUrl === "string" && config.ankiconnectUrl.trim()
      ? config.ankiconnectUrl.trim()
      : undefined;
  return {
    ankicliPath,
    collectionPath,
    backend,
    ankiconnectUrl,
  };
}

export function buildCliArgv(config, commandArgs) {
  const argv = ["--json"];
  if (config.backend) {
    argv.push("--backend", config.backend);
  }
  if (config.collectionPath) {
    argv.push("--collection", config.collectionPath);
  }
  argv.push(...commandArgs);
  return argv;
}

export async function runSubprocessOnce({ execPath, argv, env, timeoutMs, maxStdoutBytes }) {
  return await new Promise((resolve, reject) => {
    const child = spawn(execPath, argv, {
      env: { ...process.env, ...env },
      stdio: ["ignore", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";
    let stdoutBytes = 0;
    let settled = false;

    const settle = (result) => {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timer);
      if (result.ok) {
        resolve(result.value);
      } else {
        reject(result.error);
      }
    };

    const failAndTerminate = (message) => {
      try {
        child.kill("SIGKILL");
      } finally {
        settle({ ok: false, error: new Error(message) });
      }
    };

    child.stdout?.setEncoding("utf8");
    child.stderr?.setEncoding("utf8");

    child.stdout?.on("data", (chunk) => {
      const value = String(chunk);
      stdoutBytes += Buffer.byteLength(value, "utf8");
      if (stdoutBytes > maxStdoutBytes) {
        failAndTerminate("ankicli output exceeded maxStdoutBytes");
        return;
      }
      stdout += value;
    });

    child.stderr?.on("data", (chunk) => {
      stderr += String(chunk);
    });

    const timer = setTimeout(() => {
      failAndTerminate("ankicli subprocess timed out");
    }, Math.max(200, timeoutMs));

    child.once("error", (error) => {
      settle({ ok: false, error });
    });

    child.once("exit", (exitCode) => {
      settle({ ok: true, value: { stdout, stderr, exitCode } });
    });
  });
}

function runSubprocessSync({ execPath, argv, env, timeoutMs, maxStdoutBytes }) {
  const result = spawnSync(execPath, argv, {
    env: { ...process.env, ...env },
    encoding: "utf8",
    timeout: Math.max(200, timeoutMs),
    maxBuffer: maxStdoutBytes,
  });
  if (result.error) {
    throw result.error;
  }
  return {
    stdout: result.stdout ?? "",
    stderr: result.stderr ?? "",
    exitCode: result.status ?? 0,
  };
}

export function parseEnvelope(stdout) {
  const trimmed = stdout.trim();
  const tryParse = (value) => {
    try {
      return JSON.parse(value);
    } catch {
      return undefined;
    }
  };

  let parsed = tryParse(trimmed);
  if (parsed === undefined) {
    const suffixMatch = trimmed.match(/({[\s\S]*}|\[[\s\S]*])\s*$/);
    if (suffixMatch?.[1]) {
      parsed = tryParse(suffixMatch[1]);
    }
  }

  if (parsed === undefined || !parsed || typeof parsed !== "object") {
    throw new Error("ankicli returned invalid JSON");
  }
  if (typeof parsed.ok !== "boolean" || typeof parsed.backend !== "string") {
    throw new Error("ankicli returned invalid JSON envelope");
  }
  return parsed;
}

function buildErrorFromEnvelope(envelope) {
  const code = envelope.error?.code ?? "ANKICLI_ERROR";
  const message = envelope.error?.message ?? "ankicli command failed";
  const error = new Error(`${code}: ${message}`);
  error.name = "AnkiCliToolError";
  error.code = code;
  error.details = envelope.error?.details;
  error.backend = envelope.backend;
  return error;
}

export async function runAnkicliJson(api, commandArgs, options = {}) {
  const config = resolvePluginConfig(api);
  const argv = buildCliArgv(config, commandArgs);
  const env =
    config.ankiconnectUrl !== undefined ? { ANKICONNECT_URL: config.ankiconnectUrl } : {};

  let result;
  try {
    result = await runSubprocessOnce({
      execPath: config.ankicliPath,
      argv,
      env,
      timeoutMs: options.timeoutMs ?? 20_000,
      maxStdoutBytes: options.maxStdoutBytes ?? 1_000_000,
    });
  } catch (error) {
    if (error?.code === "ENOENT") {
      throw new Error(`ankicli executable not found: ${config.ankicliPath}`);
    }
    throw error;
  }

  const envelope = parseEnvelope(result.stdout);
  if (!envelope.ok) {
    throw buildErrorFromEnvelope(envelope);
  }
  return envelope;
}

export function runAnkicliJsonSync(api, commandArgs, options = {}) {
  const config = resolvePluginConfig(api);
  const argv = buildCliArgv(config, commandArgs);
  const env =
    config.ankiconnectUrl !== undefined ? { ANKICONNECT_URL: config.ankiconnectUrl } : {};
  let result;
  try {
    result = runSubprocessSync({
      execPath: config.ankicliPath,
      argv,
      env,
      timeoutMs: options.timeoutMs ?? 20_000,
      maxStdoutBytes: options.maxStdoutBytes ?? 1_000_000,
    });
  } catch (error) {
    if (error?.code === "ENOENT") {
      throw new Error(`ankicli executable not found: ${config.ankicliPath}`);
    }
    throw error;
  }
  const envelope = parseEnvelope(result.stdout);
  if (!envelope.ok) {
    throw buildErrorFromEnvelope(envelope);
  }
  return envelope;
}

export function loadCatalogSync(api) {
  const envelope = runAnkicliJsonSync(api, ["catalog", "export"], {
    timeoutMs: 8_000,
    maxStdoutBytes: 1_000_000,
  });
  return envelope.data ?? {};
}

function appendFieldArgs(args, fields) {
  for (const [name, value] of Object.entries(fields ?? {})) {
    args.push("--field", `${name}=${value}`);
  }
}

function appendTagArgs(args, tags) {
  for (const tag of tags ?? []) {
    args.push("--tag", tag);
  }
}

function buildSearchArgs(kind, query, limit, offset) {
  const args = ["search", kind, "--query", query];
  if (typeof limit === "number") {
    args.push("--limit", String(limit));
  }
  if (typeof offset === "number") {
    args.push("--offset", String(offset));
  }
  return args;
}

function buildStudySessionArgs(commandArgs, params) {
  const args = [...commandArgs];
  if (typeof params.sessionId === "string" && params.sessionId.trim()) {
    args.push("--session-id", params.sessionId.trim());
  }
  return args;
}

function buildCardMutationArgs(commandArgs, params) {
  const args = [...commandArgs, "--id", String(params.id)];
  if (params.yes === true) {
    args.push("--yes");
  }
  if (params.dryRun === true) {
    args.push("--dry-run");
  }
  return args;
}

function normalizeFreeformCommand(command) {
  const tokens = splitCommandString(command);
  if (tokens.length === 0) {
    throw new Error("ankicli command is required");
  }

  const normalized = [...tokens];
  if (normalized[0] === "ankicli") {
    normalized.shift();
  }

  const filtered = normalized.filter((token) => token !== "--json");
  if (filtered.length === 0) {
    throw new Error("ankicli command is required");
  }
  return filtered;
}

function splitCommandString(command) {
  if (typeof command !== "string") {
    return [];
  }

  const tokens = [];
  let current = "";
  let quote = null;
  let escaping = false;

  for (const char of command) {
    if (escaping) {
      current += char;
      escaping = false;
      continue;
    }
    if (char === "\\") {
      escaping = true;
      continue;
    }
    if (quote !== null) {
      if (char === quote) {
        quote = null;
      } else {
        current += char;
      }
      continue;
    }
    if (char === "'" || char === '"') {
      quote = char;
      continue;
    }
    if (/\s/.test(char)) {
      if (current) {
        tokens.push(current);
        current = "";
      }
      continue;
    }
    current += char;
  }

  if (escaping) {
    current += "\\";
  }
  if (quote !== null) {
    throw new Error("ankicli command has an unclosed quote");
  }
  if (current) {
    tokens.push(current);
  }

  return tokens;
}

function buildNoteManageArgs(params) {
  switch (params.action) {
    case "get":
      return ["note", "get", "--id", String(params.id)];
    case "fields":
      return ["note", "fields", "--id", String(params.id)];
    case "add": {
      const args = ["note", "add", "--deck", params.deck, "--model", params.model];
      appendFieldArgs(args, params.fields);
      appendTagArgs(args, params.tags);
      if (params.dryRun === true) {
        args.push("--dry-run");
      }
      return args;
    }
    case "update": {
      const args = ["note", "update", "--id", String(params.id)];
      appendFieldArgs(args, params.fields);
      if (params.dryRun === true) {
        args.push("--dry-run");
      }
      return args;
    }
    case "delete": {
      const args = ["note", "delete", "--id", String(params.id)];
      if (params.yes === true) {
        args.push("--yes");
      }
      if (params.dryRun === true) {
        args.push("--dry-run");
      }
      return args;
    }
    case "add_tags":
    case "remove_tags": {
      const args = [
        "note",
        params.action === "add_tags" ? "add-tags" : "remove-tags",
        "--id",
        String(params.id),
      ];
      appendTagArgs(args, params.tags);
      if (params.yes === true) {
        args.push("--yes");
      }
      if (params.dryRun === true) {
        args.push("--dry-run");
      }
      return args;
    }
    case "move_deck": {
      const args = ["note", "move-deck", "--id", String(params.id), "--deck", params.deck];
      if (params.yes === true) {
        args.push("--yes");
      }
      if (params.dryRun === true) {
        args.push("--dry-run");
      }
      return args;
    }
    default:
      throw new Error(`Unsupported note action: ${String(params.action)}`);
  }
}

function buildDeckManageArgs(params) {
  switch (params.action) {
    case "list":
      return ["deck", "list"];
    case "get":
      return ["deck", "get", "--name", params.name];
    case "stats":
      return ["deck", "stats", "--name", params.name];
    case "create": {
      const args = ["deck", "create", "--name", params.name];
      if (params.yes === true) {
        args.push("--yes");
      }
      if (params.dryRun === true) {
        args.push("--dry-run");
      }
      return args;
    }
    case "rename": {
      const args = ["deck", "rename", "--name", params.name, "--to", params.to];
      if (params.yes === true) {
        args.push("--yes");
      }
      if (params.dryRun === true) {
        args.push("--dry-run");
      }
      return args;
    }
    case "delete": {
      const args = ["deck", "delete", "--name", params.name];
      if (params.yes === true) {
        args.push("--yes");
      }
      if (params.dryRun === true) {
        args.push("--dry-run");
      }
      return args;
    }
    case "reparent": {
      const args = ["deck", "reparent", "--name", params.name];
      if (typeof params.toParent === "string") {
        args.push("--to-parent", params.toParent);
      }
      if (params.yes === true) {
        args.push("--yes");
      }
      if (params.dryRun === true) {
        args.push("--dry-run");
      }
      return args;
    }
    default:
      throw new Error(`Unsupported deck action: ${String(params.action)}`);
  }
}

function buildStudyStartArgs(params) {
  const args = ["study", "start"];
  if (typeof params.deck === "string" && params.deck.trim()) {
    args.push("--deck", params.deck.trim());
  }
  if (typeof params.query === "string" && params.query.trim()) {
    args.push("--query", params.query.trim());
  }
  if (typeof params.scopePreset === "string" && params.scopePreset.trim()) {
    args.push("--scope-preset", params.scopePreset.trim());
  }
  if (typeof params.limit === "number") {
    args.push("--limit", String(params.limit));
  }
  return args;
}

function buildSearchUnifiedArgs(params) {
  const kind = params.kind === "notes" ? "notes" : "cards";
  if (params.preview === true) {
    const args = ["search", "preview", "--kind", kind, "--query", params.query ?? ""];
    if (typeof params.limit === "number") {
      args.push("--limit", String(params.limit));
    }
    if (typeof params.offset === "number") {
      args.push("--offset", String(params.offset));
    }
    return args;
  }
  return buildSearchArgs(kind, params.query ?? "", params.limit, params.offset);
}

function buildCommandArgs(spec, params) {
  switch (spec.command.mode) {
    case "fixed":
      return [...(spec.command.argv ?? [])];
    case "fixed-search":
      return buildSearchArgs(spec.command.argv?.[1], params.query, params.limit, params.offset);
    case "fixed-id":
      return [...(spec.command.argv ?? []), "--id", String(params.id)];
    case "legacy-note-add": {
      const args = ["note", "add", "--deck", params.deck, "--model", params.model];
      appendFieldArgs(args, params.fields);
      appendTagArgs(args, params.tags);
      if (params.dryRun === true) {
        args.push("--dry-run");
      }
      return args;
    }
    case "legacy-note-update": {
      const args = ["note", "update", "--id", String(params.id)];
      appendFieldArgs(args, params.fields);
      if (params.dryRun === true) {
        args.push("--dry-run");
      }
      return args;
    }
    case "card-mutation":
      return buildCardMutationArgs(spec.command.argv ?? [], params);
    case "search-unified":
      return buildSearchUnifiedArgs(params);
    case "note-manage":
      return buildNoteManageArgs(params);
    case "deck-manage":
      return buildDeckManageArgs(params);
    case "study-start":
      return buildStudyStartArgs(params);
    case "study-session":
      return buildStudySessionArgs(spec.command.argv ?? [], params);
    case "study-grade": {
      const args = ["study", "grade", "--rating", params.rating];
      if (typeof params.sessionId === "string" && params.sessionId.trim()) {
        args.push("--session-id", params.sessionId.trim());
      }
      return args;
    }
    case "freeform":
      return normalizeFreeformCommand(params.command);
    default:
      throw new Error(`Unsupported tool command mode: ${String(spec.command.mode)}`);
  }
}

function summarizeContent(spec, data) {
  if (spec.workflow_id?.startsWith("study.")) {
    return JSON.stringify(data, null, 2);
  }
  return JSON.stringify(data, null, 2);
}

function isRecord(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function cloneJson(value) {
  return value === undefined ? undefined : JSON.parse(JSON.stringify(value));
}

function normalizePreviewPaneHtml(value) {
  const normalized = typeof value === "string" ? value.trim() : "";
  if (!normalized) {
    return undefined;
  }
  const headMatch = normalized.match(/<head\b[^>]*>([\s\S]*?)<\/head>/i);
  const bodyMatch = normalized.match(/<body\b[^>]*>([\s\S]*?)<\/body>/i);
  if (!headMatch && !bodyMatch) {
    return normalized;
  }
  const headContent = headMatch?.[1] ?? "";
  const renderableHeadTags = Array.from(
    headContent.matchAll(/<(style|script)\b[\s\S]*?<\/\1>|<link\b[^>]*>/gi),
    (match) => match[0],
  ).join("");
  const bodyContent = bodyMatch?.[1]?.trim() ?? normalized;
  return `${renderableHeadTags}${bodyContent}`.trim();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function previewSpecToCanvasInput(previewSpec) {
  if (!isRecord(previewSpec) || previewSpec.kind !== "anki_card_preview") {
    return null;
  }
  const front = normalizePreviewPaneHtml(previewSpec.front);
  const back = normalizePreviewPaneHtml(previewSpec.back);
  if (!front && !back) {
    return null;
  }
  const hasBack = Boolean(back);
  const defaultSide = hasBack ? "back" : "front";
  const indexHtml = `<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>${escapeHtml(typeof previewSpec.title === "string" ? previewSpec.title : "Preview")}</title>
    <style>
      html, body { margin: 0; padding: 0; background: #ffffff; color: #111111; font: 16px/1.5 system-ui, sans-serif; }
      body { padding: 16px; }
      .preview-tabs { display: ${hasBack ? "flex" : "none"}; gap: 8px; margin-bottom: 12px; }
      .preview-tab { border: 1px solid #d0d7de; background: #f6f8fa; border-radius: 999px; padding: 6px 12px; cursor: pointer; }
      .preview-tab.is-active { background: #111827; color: #fff; border-color: #111827; }
      .preview-panel[hidden] { display: none; }
    </style>
  </head>
  <body>
    <div class="preview-tabs">
      <button type="button" class="preview-tab ${defaultSide === "front" ? "is-active" : ""}" data-side="front">Front</button>
      <button type="button" class="preview-tab ${defaultSide === "back" ? "is-active" : ""}" data-side="back">Back</button>
    </div>
    <section class="preview-panel" data-side="front" ${defaultSide === "back" ? "hidden" : ""}>${front ?? ""}</section>
    <section class="preview-panel" data-side="back" ${defaultSide === "front" ? "hidden" : ""}>${back ?? ""}</section>
    <script>
      const tabs = Array.from(document.querySelectorAll(".preview-tab"));
      const panels = Array.from(document.querySelectorAll(".preview-panel"));
      tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
          const side = tab.getAttribute("data-side");
          tabs.forEach((entry) => entry.classList.toggle("is-active", entry === tab));
          panels.forEach((panel) => { panel.hidden = panel.getAttribute("data-side") !== side; });
        });
      });
    </script>
  </body>
</html>`;
  return {
    kind: "html_bundle",
    ...(typeof previewSpec.title === "string" && previewSpec.title.trim()
      ? { title: previewSpec.title.trim() }
      : {}),
    ...(typeof previewSpec.preferredHeight === "number"
      ? { preferredHeight: previewSpec.preferredHeight }
      : {}),
    entrypoint: {
      type: "html",
      value: indexHtml,
    },
    assets: Array.isArray(previewSpec.assets) ? cloneJson(previewSpec.assets) : [],
  };
}

async function materializeCardViewHandle(api, cardPayload) {
  if (!isRecord(cardPayload)) {
    return cardPayload;
  }
  const previewSpec = isRecord(cardPayload.preview_spec) ? cardPayload.preview_spec : null;
  const studyMediaSpec = isRecord(cardPayload.study_media_spec) ? cardPayload.study_media_spec : null;
  const nextCard = {};
  for (const key of [
    "card_id",
    "note_id",
    "deck_id",
    "revealed",
    "position",
    "remaining",
    "miss_history",
    "miss_count",
    "rating",
  ]) {
    if (key in cardPayload) {
      nextCard[key] = cloneJson(cardPayload[key]);
    }
  }
  if (cardPayload.tutoring_summary !== undefined) {
    nextCard.tutoring_summary = cloneJson(cardPayload.tutoring_summary);
  }
  const canvasInput = previewSpecToCanvasInput(previewSpec);
  if (!canvasInput) {
    return nextCard;
  }
  const document = await api.createCanvasDocument(cloneJson(canvasInput));
  const documentId =
    typeof document?.docId === "string" && document.docId
      ? document.docId
      : typeof document?.id === "string" && document.id
        ? document.id
        : null;
  const assetByLogicalPath = new Map(
    Array.isArray(document.assets)
      ? document.assets.map((entry) => [String(entry.logicalPath), entry])
      : [],
  );
  if (!documentId || typeof document.entryUrl !== "string" || !document.entryUrl) {
    return nextCard;
  }
  return {
    ...nextCard,
    view: {
      backend: "canvas",
      id: documentId,
      url: document.entryUrl,
      ...(document.title ? { title: document.title } : {}),
      ...(typeof document.preferredHeight === "number"
        ? { preferred_height: document.preferredHeight }
        : {}),
    },
    ...(studyMediaSpec ? { study_media: compactStudyMedia(studyMediaSpec, assetByLogicalPath) } : {}),
  };
}

function compactStudyMedia(studyMediaSpec, assetByLogicalPath) {
  const projectMediaList = (entries) =>
    Array.isArray(entries)
      ? entries
          .map((entry) => {
            if (!isRecord(entry)) {
              return null;
            }
            const logicalPath =
              typeof entry.logicalPath === "string" && entry.logicalPath.trim()
                ? entry.logicalPath.trim()
                : null;
            if (!logicalPath) {
              return null;
            }
            const asset = assetByLogicalPath.get(logicalPath);
            const mediaHandle =
              typeof asset?.localPath === "string" && asset.localPath.trim()
                ? asset.localPath.trim()
                : typeof asset?.url === "string" && asset.url.trim()
                  ? asset.url.trim()
                  : null;
            if (!mediaHandle) {
              return null;
            }
            const projected = {
              asset_id: `asset:${logicalPath}`,
              media_url: mediaHandle,
              logical_path: logicalPath,
            };
            for (const [fromKey, toKey] of [
              ["role", "role"],
              ["label", "label"],
              ["contentType", "content_type"],
              ["field", "field"],
            ]) {
              const value = entry[fromKey];
              if (typeof value === "string" && value.trim()) {
                projected[toKey] = value.trim();
              }
            }
            return projected;
          })
          .filter(Boolean)
      : [];

  const degraded = Array.isArray(studyMediaSpec.degraded)
    ? studyMediaSpec.degraded
        .map((entry) => {
          if (!isRecord(entry)) {
            return null;
          }
          const logicalPath =
            typeof entry.logicalPath === "string" && entry.logicalPath.trim()
              ? entry.logicalPath.trim()
              : null;
          const errorCode =
            typeof entry.errorCode === "string" && entry.errorCode.trim()
              ? entry.errorCode.trim()
              : null;
          if (!logicalPath || !errorCode) {
            return null;
          }
          return {
            logical_path: logicalPath,
            error_code: errorCode,
            ...(typeof entry.kind === "string" && entry.kind.trim()
              ? { kind: entry.kind.trim() }
              : {}),
            ...(typeof entry.tag === "string" && entry.tag.trim() ? { tag: entry.tag.trim() } : {}),
          };
        })
        .filter(Boolean)
    : [];

  return {
    audio: projectMediaList(studyMediaSpec.audio),
    answer_audio: projectMediaList(studyMediaSpec.answer_audio),
    images: projectMediaList(studyMediaSpec.images),
    degraded,
  };
}

async function buildModelFacingStudyData(api, data) {
  if (!isRecord(data)) {
    return data;
  }
  const next = { ...data };
  if ("current_card" in next) {
    next.current_card = await materializeCardViewHandle(api, next.current_card);
  }
  if ("next_card" in next) {
    next.next_card = await materializeCardViewHandle(api, next.next_card);
  }
  if ("graded_card" in next) {
    next.graded_card = await materializeCardViewHandle(api, next.graded_card);
  }
  return next;
}

function shouldPromoteStudyCanvas(spec) {
  const workflowId = typeof spec?.workflow_id === "string" ? spec.workflow_id : "";
  return workflowId === "study.details" || workflowId === "study.reveal";
}

function promoteStudyCanvasPayload(data) {
  if (!isRecord(data)) {
    return data;
  }
  const currentCard = isRecord(data.current_card) ? data.current_card : null;
  const view = currentCard && isRecord(currentCard.view) ? currentCard.view : null;
  if (!view) {
    return data;
  }
  const next = {
    kind: "canvas",
    ...data,
    view: cloneJson(view),
    presentation: {
      target: "assistant_message",
    },
  };
  return next;
}

function buildWorkflowIndex(catalog) {
  const workflows = Array.isArray(catalog?.workflows) ? catalog.workflows : [];
  return new Map(workflows.map((workflow) => [workflow.id, workflow]));
}

function buildUnsupportedActionError({ backend, workflowId, actionId, fallbackHint }) {
  const message = `${workflowId} action '${actionId}' is not supported by the ${backend} backend`;
  const error = new Error(`BACKEND_ACTION_UNSUPPORTED: ${message}`);
  error.name = "AnkiCliToolError";
  error.code = "BACKEND_ACTION_UNSUPPORTED";
  error.details = {
    backend,
    workflow_id: workflowId,
    action_id: actionId,
    recommended_fallback: fallbackHint ?? null,
  };
  error.backend = backend;
  return error;
}

function findActionSpec(workflow, actionId) {
  const actions = Array.isArray(workflow?.actions) ? workflow.actions : [];
  return actions.find((action) => action.id === actionId) ?? null;
}

function assertSupportedWorkflowAction(catalog, spec, params) {
  const workflowId = spec.workflow_id;
  if (workflowId !== "deck.manage" && workflowId !== "note.manage") {
    return;
  }
  const actionId = typeof params.action === "string" ? params.action.trim() : "";
  if (!actionId) {
    return;
  }
  const workflowSupport = catalog?.workflow_support?.[workflowId];
  const actionSupport = workflowSupport?.actions ?? {};
  if (actionSupport[actionId] !== false) {
    return;
  }
  const workflows = buildWorkflowIndex(catalog);
  const actionSpec = findActionSpec(workflows.get(workflowId), actionId);
  throw buildUnsupportedActionError({
    backend: String(catalog?.backend ?? "unknown"),
    workflowId,
    actionId,
    fallbackHint: actionSpec?.fallback_hint ?? null,
  });
}

export function createAnkiCliTool(api, spec, catalog = {}) {
  return {
    name: spec.name,
    label: spec.label,
    description: spec.description,
    parameters: spec.parameter_schema,
    async execute(_toolCallId, rawParams) {
      const params = rawParams ?? {};
      assertSupportedWorkflowAction(catalog, spec, params);
      const envelope = await runAnkicliJson(api, buildCommandArgs(spec, params));
      const rawData = envelope.data ?? {};
      let data = spec.workflow_id?.startsWith("study.")
        ? await buildModelFacingStudyData(api, rawData)
        : rawData;
      if (shouldPromoteStudyCanvas(spec)) {
        data = promoteStudyCanvasPayload(data);
      }
      return {
        content: [
          {
            type: "text",
            text: summarizeContent(spec, data),
          },
        ],
        details: {
          backend: envelope.backend,
          data,
          rawData,
          meta: envelope.meta ?? {},
          workflowId: spec.workflow_id ?? null,
          surface: spec.surface,
        },
      };
    },
  };
}
