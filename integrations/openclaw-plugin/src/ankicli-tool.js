import { spawn } from "node:child_process";
import path from "node:path";

const BACKEND_VALUES = new Set(["python-anki", "ankiconnect"]);

function objectSchema(properties, required = []) {
  return {
    type: "object",
    additionalProperties: false,
    properties,
    ...(required.length ? { required } : {}),
  };
}

const emptySchema = objectSchema({});

const fieldsSchema = {
  type: "object",
  additionalProperties: {
    type: "string",
  },
};

export const toolSpecs = [
  {
    name: "anki_collection_info",
    label: "Anki Collection Info",
    description: "Fetch high-level collection metadata and counts through ankicli.",
    parameters: emptySchema,
    buildArgs: () => ["collection", "info"],
    summarize: (data) =>
      `Fetched collection info (backend_available=${String(data.backend_available ?? "unknown")}).`,
  },
  {
    name: "anki_auth_status",
    label: "Anki Auth Status",
    description: "Report whether sync credentials are available through ankicli.",
    parameters: emptySchema,
    buildArgs: () => ["auth", "status"],
    summarize: (data) =>
      `Auth status fetched (authenticated=${String(data.authenticated ?? false)}).`,
  },
  {
    name: "anki_sync_status",
    label: "Anki Sync Status",
    description: "Check whether the configured collection requires sync through ankicli.",
    parameters: emptySchema,
    buildArgs: () => ["sync", "status"],
    summarize: (data) =>
      `Sync status fetched (required=${String(data.required ?? "unknown")}).`,
  },
  {
    name: "anki_sync_run",
    label: "Anki Sync Run",
    description: "Run the normal collection sync flow through ankicli.",
    parameters: emptySchema,
    buildArgs: () => ["sync", "run"],
    summarize: (data) =>
      `Sync run completed (performed=${String(data.performed ?? false)}).`,
  },
  {
    name: "anki_deck_list",
    label: "Anki Deck List",
    description: "List decks in the configured collection through ankicli.",
    parameters: emptySchema,
    buildArgs: () => ["deck", "list"],
    summarize: (data) => `Returned ${countItems(data)} decks.`,
  },
  {
    name: "anki_model_list",
    label: "Anki Model List",
    description: "List note types in the configured collection through ankicli.",
    parameters: emptySchema,
    buildArgs: () => ["model", "list"],
    summarize: (data) => `Returned ${countItems(data)} note types.`,
  },
  {
    name: "anki_search_notes",
    label: "Anki Search Notes",
    description: "Search note ids with an Anki-style query through ankicli.",
    parameters: objectSchema(
      {
        query: { type: "string" },
        limit: { type: "number", minimum: 0 },
        offset: { type: "number", minimum: 0 },
      },
      ["query"],
    ),
    buildArgs: (params) => buildSearchArgs("notes", params.query, params.limit, params.offset),
    summarize: (data) =>
      `Returned ${countItems(data)} notes (total=${String(data.total ?? countItems(data))}).`,
  },
  {
    name: "anki_search_cards",
    label: "Anki Search Cards",
    description: "Search card ids with an Anki-style query through ankicli.",
    parameters: objectSchema(
      {
        query: { type: "string" },
        limit: { type: "number", minimum: 0 },
        offset: { type: "number", minimum: 0 },
      },
      ["query"],
    ),
    buildArgs: (params) => buildSearchArgs("cards", params.query, params.limit, params.offset),
    summarize: (data) =>
      `Returned ${countItems(data)} cards (total=${String(data.total ?? countItems(data))}).`,
  },
  {
    name: "anki_note_get",
    label: "Anki Note Get",
    description: "Fetch one normalized note record by id through ankicli.",
    parameters: objectSchema(
      {
        id: { type: "number" },
      },
      ["id"],
    ),
    buildArgs: (params) => ["note", "get", "--id", String(params.id)],
    summarize: (data) => `Fetched note ${String(data.id ?? "?")}.`,
  },
  {
    name: "anki_note_add",
    label: "Anki Note Add",
    description: "Add a note through ankicli with optional dry-run safety.",
    parameters: objectSchema(
      {
        deck: { type: "string" },
        model: { type: "string" },
        fields: fieldsSchema,
        tags: {
          type: "array",
          items: { type: "string" },
        },
        dryRun: { type: "boolean" },
      },
      ["deck", "model", "fields"],
    ),
    buildArgs: (params) => {
      const args = ["note", "add", "--deck", params.deck, "--model", params.model];
      appendFieldArgs(args, params.fields);
      appendTagArgs(args, params.tags);
      if (params.dryRun === true) {
        args.push("--dry-run");
      }
      return args;
    },
    summarize: (data) =>
      `Note add completed for note ${String(data.id ?? "?")} (dry_run=${String(data.dry_run ?? false)}).`,
  },
  {
    name: "anki_note_update",
    label: "Anki Note Update",
    description: "Update note fields through ankicli with optional dry-run safety.",
    parameters: objectSchema(
      {
        id: { type: "number" },
        fields: fieldsSchema,
        dryRun: { type: "boolean" },
      },
      ["id", "fields"],
    ),
    buildArgs: (params) => {
      const args = ["note", "update", "--id", String(params.id)];
      appendFieldArgs(args, params.fields);
      if (params.dryRun === true) {
        args.push("--dry-run");
      }
      return args;
    },
    summarize: (data) =>
      `Note update completed for note ${String(data.id ?? "?")} (dry_run=${String(data.dry_run ?? false)}).`,
  },
  {
    name: "anki_card_suspend",
    label: "Anki Card Suspend",
    description: "Suspend a card through ankicli with explicit yes/dry-run flags.",
    parameters: objectSchema(
      {
        id: { type: "number" },
        yes: { type: "boolean" },
        dryRun: { type: "boolean" },
      },
      ["id"],
    ),
    buildArgs: (params) => buildCardMutationArgs("suspend", params.id, params.yes, params.dryRun),
    summarize: (data) =>
      `Card ${String(data.id ?? "?")} suspend result (dry_run=${String(data.dry_run ?? false)}).`,
  },
  {
    name: "anki_card_unsuspend",
    label: "Anki Card Unsuspend",
    description: "Unsuspend a card through ankicli with explicit yes/dry-run flags.",
    parameters: objectSchema(
      {
        id: { type: "number" },
        yes: { type: "boolean" },
        dryRun: { type: "boolean" },
      },
      ["id"],
    ),
    buildArgs: (params) =>
      buildCardMutationArgs("unsuspend", params.id, params.yes, params.dryRun),
    summarize: (data) =>
      `Card ${String(data.id ?? "?")} unsuspend result (dry_run=${String(data.dry_run ?? false)}).`,
  },
];

function countItems(data) {
  return Array.isArray(data?.items) ? data.items.length : 0;
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

function buildCardMutationArgs(command, id, yes, dryRun) {
  const args = ["card", command, "--id", String(id)];
  if (yes === true) {
    args.push("--yes");
  }
  if (dryRun === true) {
    args.push("--dry-run");
  }
  return args;
}

function resolvePluginConfig(api) {
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

function buildCliArgv(config, commandArgs) {
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

async function runSubprocessOnce({ execPath, argv, env, timeoutMs, maxStdoutBytes }) {
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

function parseEnvelope(stdout) {
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

function renderToolText(spec, data) {
  if (typeof spec.summarize === "function") {
    return `${spec.summarize(data)}\n${JSON.stringify(data, null, 2)}`;
  }
  return JSON.stringify(data, null, 2);
}

export function createAnkiCliTool(api, spec) {
  return {
    name: spec.name,
    label: spec.label,
    description: spec.description,
    parameters: spec.parameters,
    async execute(_toolCallId, rawParams) {
      const config = resolvePluginConfig(api);
      const argv = buildCliArgv(config, spec.buildArgs(rawParams ?? {}));
      const env =
        config.ankiconnectUrl !== undefined ? { ANKICONNECT_URL: config.ankiconnectUrl } : {};

      let result;
      try {
        result = await runSubprocessOnce({
          execPath: config.ankicliPath,
          argv,
          env,
          timeoutMs: 20_000,
          maxStdoutBytes: 1_000_000,
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

      const data = envelope.data ?? {};
      return {
        content: [
          {
            type: "text",
            text: renderToolText(spec, data),
          },
        ],
        details: {
          backend: envelope.backend,
          data,
          meta: envelope.meta ?? {},
        },
      };
    },
  };
}
