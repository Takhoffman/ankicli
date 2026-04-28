import { chmodSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

import plugin from "../index.js";
import { buildCliArgv, resolvePluginConfig } from "../src/ankicli-tool.js";

function createFakeAnkicli({ studyDetails, studyRevealData, studyStartData } = {}) {
  const dir = mkdtempSync(path.join(os.tmpdir(), "ankicli-plugin-test-"));
  const scriptPath = path.join(dir, "fake-ankicli.mjs");
  const commandPath =
    process.platform === "win32" ? path.join(dir, "fake-ankicli.cmd") : scriptPath;
  const serializedStudyDetails = JSON.stringify(
    studyDetails ?? {
      session: {
        id: "session-1",
        status: "active",
        completed_count: 1,
        remaining_count: 2,
      },
      current_card: {
        card_id: 101,
        revealed: false,
        preview_spec: {
          kind: "anki_card_preview",
          title: "Listen to a word in a sentence",
          preferredHeight: 420,
          front: "<div>front</div>",
          assets: [{ logicalPath: "collection.media/audio.mp3", sourcePath: "/tmp/audio.mp3" }],
        },
        study_view: {
          answer: null,
          back_card_text: null,
        },
        tutoring_summary: {
          template: "Listen to a word in a sentence",
          prompt: "それ",
          meaning: "that",
          reveal_state: "front_only",
          media: {
            audio_slots: 1,
            images: 0,
            degraded: [],
          },
        },
        study_media_spec: {
          audio: [
            {
              role: "prompt_audio",
              label: "Prompt audio 1",
              logicalPath: "collection.media/audio.mp3",
              contentType: "audio/mpeg",
            },
          ],
          answer_audio: [],
          images: [],
          degraded: [],
        },
      },
    },
  );
  const serializedStudyStartData = JSON.stringify(
    studyStartData ?? {
      session: {
        id: "session-1",
        status: "active",
      },
      current_card: {
        card_id: 101,
        preview_spec: {
          kind: "anki_card_preview",
          title: "Listen to a word in a sentence",
          preferredHeight: 420,
          front: "<div>front</div>",
          back: "<div>back</div>",
          assets: [{ logicalPath: "collection.media/audio.mp3", sourcePath: "/tmp/audio.mp3" }],
        },
        tutoring_summary: {
          template: "Listen to a word in a sentence",
          prompt: "それ",
          meaning: "that",
          reveal_state: "front_only",
          media: {
            audio_slots: 1,
            images: 0,
            degraded: [],
          },
        },
        study_media_spec: {
          audio: [
            {
              role: "prompt_audio",
              label: "Prompt audio 1",
              logicalPath: "collection.media/audio.mp3",
              contentType: "audio/mpeg",
            },
          ],
          answer_audio: [],
          images: [],
          degraded: [],
        },
      },
    },
  );
  const serializedStudyRevealData = JSON.stringify(
    studyRevealData ?? {
      session: {
        id: "session-1",
        status: "active",
        completed_count: 1,
        remaining_count: 2,
      },
      current_card: {
        card_id: 101,
        revealed: true,
        answer: "that",
        preview_spec: {
          kind: "anki_card_preview",
          title: "Listen to a word in a sentence",
          preferredHeight: 420,
          front: "<div>front</div>",
          back: "<div>back</div>",
          assets: [{ logicalPath: "collection.media/audio.mp3", sourcePath: "/tmp/audio.mp3" }],
        },
        study_view: {
          answer: "that",
          back_card_text: "that",
        },
        tutoring_summary: {
          template: "Listen to a word in a sentence",
          prompt: "それ",
          meaning: "that",
          reveal_state: "answer_revealed",
          media: {
            audio_slots: 1,
            images: 0,
            degraded: [],
          },
        },
        study_media_spec: {
          audio: [
            {
              role: "prompt_audio",
              label: "Prompt audio 1",
              logicalPath: "collection.media/audio.mp3",
              contentType: "audio/mpeg",
            },
          ],
          answer_audio: [],
          images: [],
          degraded: [],
        },
      },
    },
  );
  const script = `#!/usr/bin/env node
const args = process.argv.slice(2);
const payload = {
  ok: true,
  backend: "ankiconnect",
  data: {},
  meta: {},
};
if (args.includes("catalog") && args.includes("export")) {
  payload.data = {
    schema_version: "2026-03-27.1",
    backend: "ankiconnect",
    available: true,
    supported_workflows: {
      "study.start": true,
      "study.details": true,
      "study.summary": true,
      "study.grade.local": true,
      "study.grade.backend": false,
      "collection.status": true,
    },
    workflow_support: {
      "study.grade.backend": { supported: false, actions: {} },
      "deck.manage": {
        supported: true,
        actions: {
          list: true,
          stats: true,
          create: false,
        },
      },
    },
    workflows: [
      { id: "study.start", kind: "primary", description: "start" },
      { id: "study.details", kind: "primary", description: "details" },
      { id: "study.summary", kind: "primary", description: "summary" },
      { id: "collection.status", kind: "primary", description: "status" },
      {
        id: "deck.manage",
        kind: "primary",
        description: "deck manage",
        actions: [
          { id: "list", fallback_hint: null },
          {
            id: "create",
            fallback_hint: "Switch to the python-anki backend for deck creation.",
          },
          { id: "stats", fallback_hint: null },
        ],
      },
    ],
    plugin_tools: [
      {
        name: "anki_collection_status",
        label: "Anki Collection Status",
        description: "status",
        surface: "primary",
        workflow_id: "collection.status",
        parameter_schema: { type: "object", additionalProperties: false, properties: {} },
        command: { mode: "fixed", argv: ["collection", "info"] },
      },
      {
        name: "anki_study_start",
        label: "Anki Study Start",
        description: "start",
        surface: "primary",
        workflow_id: "study.start",
        parameter_schema: { type: "object", additionalProperties: false, properties: {} },
        command: { mode: "study-start" },
      },
      {
        name: "anki_deck_manage",
        label: "Anki Deck Manage",
        description: "deck manage",
        surface: "primary",
        workflow_id: "deck.manage",
        parameter_schema: {
          type: "object",
          additionalProperties: false,
          properties: {
            action: { type: "string", enum: ["list", "create", "stats"] },
            name: { type: "string" },
          },
          required: ["action"],
        },
        command: { mode: "deck-manage" },
      },
      {
        name: "anki_study_card_details",
        label: "Anki Study Card Details",
        description: "details",
        surface: "primary",
        workflow_id: "study.details",
        parameter_schema: { type: "object", additionalProperties: false, properties: {} },
        command: { mode: "study-session", argv: ["study", "details"] },
      },
      {
        name: "anki_study_reveal",
        label: "Anki Study Reveal",
        description: "reveal",
        surface: "primary",
        workflow_id: "study.reveal",
        parameter_schema: { type: "object", additionalProperties: false, properties: {} },
        command: { mode: "study-session", argv: ["study", "reveal"] },
      },
      {
        name: "anki_collection_info",
        label: "Anki Collection Info",
        description: "legacy",
        surface: "legacy",
        workflow_id: null,
        parameter_schema: { type: "object", additionalProperties: false, properties: {} },
        command: { mode: "fixed", argv: ["collection", "info"] },
      },
      {
        name: "ankicli",
        label: "ankicli",
        description: "expert",
        surface: "expert",
        workflow_id: "operation.invoke",
        parameter_schema: { type: "object", additionalProperties: false, properties: { command: { type: "string" } }, required: ["command"] },
        command: { mode: "freeform" },
      },
    ],
    notes: ["AnkiConnect live"],
  };
} else if (args.includes("study") && args.includes("details")) {
  payload.data = ${serializedStudyDetails};
} else if (args.includes("study") && args.includes("reveal")) {
  payload.data = ${serializedStudyRevealData};
} else if (args.includes("study") && args.includes("summary")) {
  payload.data = ${serializedStudyDetails};
} else if (args.includes("study") && args.includes("start")) {
  payload.data = ${serializedStudyStartData};
} else {
  payload.data = { ok: true };
}
console.log(JSON.stringify(payload));
`;
  writeFileSync(scriptPath, script, "utf8");
  if (process.platform === "win32") {
    writeFileSync(
      commandPath,
      `@echo off\r\n"${process.execPath}" "${scriptPath}" %*\r\n`,
      "utf8",
    );
  } else {
    chmodSync(scriptPath, 0o755);
  }
  return {
    dir,
    scriptPath: commandPath,
    cleanup() {
      rmSync(dir, { recursive: true, force: true });
    },
  };
}

test("resolvePluginConfig treats forward and backslash ankicli paths as paths on every platform", () => {
  const resolved = [];
  const api = {
    pluginConfig: {
      ankicliPath: "tools\\ankicli.cmd",
      collectionPath: "fixtures/collection.anki2",
      backend: "python-anki",
      ankiconnectUrl: "http://127.0.0.1:8765",
    },
    resolvePath(value) {
      resolved.push(value);
      return `resolved:${value}`;
    },
  };

  const config = resolvePluginConfig(api);

  assert.equal(config.ankicliPath, "resolved:tools\\ankicli.cmd");
  assert.equal(config.collectionPath, "resolved:fixtures/collection.anki2");
  assert.equal(config.backend, "python-anki");
  assert.equal(config.ankiconnectUrl, "http://127.0.0.1:8765");
  assert.deepEqual(resolved, ["tools\\ankicli.cmd", "fixtures/collection.anki2"]);
});

test("buildCliArgv preserves Windows collection paths as one argv value", () => {
  assert.deepEqual(
    buildCliArgv(
      {
        backend: "python-anki",
        collectionPath: "C:\\Users\\Ada Lovelace\\Anki\\User 1\\collection.anki2",
      },
      ["collection", "info"],
    ),
    [
      "--json",
      "--backend",
      "python-anki",
      "--collection",
      "C:\\Users\\Ada Lovelace\\Anki\\User 1\\collection.anki2",
      "collection",
      "info",
    ],
  );
});

test("register uses plugin_tools from catalog export and filters by tool mode", async () => {
  const fake = createFakeAnkicli();
  const registered = [];
  const hooks = [];
  try {
    plugin.register({
      pluginConfig: {
        ankicliPath: fake.scriptPath,
        toolMode: "llm-default",
      },
      resolvePath: (value) => value,
      registerTool(tool, meta) {
        registered.push({ tool, meta });
      },
      on(eventName, handler) {
        hooks.push({ eventName, handler });
      },
      logger: { warn() {} },
    });

    assert.deepEqual(
      registered.map((entry) => entry.meta.name),
      ["anki_collection_status", "anki_study_start", "anki_deck_manage", "anki_study_card_details", "anki_study_reveal", "ankicli"],
    );
    assert.equal(hooks[0]?.eventName, "before_prompt_build");
    const hookResult = await hooks[0].handler();
    assert.match(hookResult.appendSystemContext, /catalog_schema_version: 2026-03-27.1/);
    assert.match(hookResult.appendSystemContext, /study_mode: local-only grading/);
    assert.match(hookResult.appendSystemContext, /session_id: session-1/);
    assert.match(hookResult.appendSystemContext, /unsupported primary actions: deck\.manage\.create/);

    const deckTool = registered.find((entry) => entry.meta.name === "anki_deck_manage")?.tool;
    await assert.rejects(
      () => deckTool.execute("tool-call-1", { action: "create", name: "New Deck" }),
      (error) =>
        error?.code === "BACKEND_ACTION_UNSUPPORTED" &&
        error?.details?.recommended_fallback ===
          "Switch to the python-anki backend for deck creation.",
    );
  } finally {
    fake.cleanup();
  }
});

test("before_prompt_build adds resolved media hints for the active study card", async () => {
  const fake = createFakeAnkicli({
    studyDetails: {
      session: {
        id: "session-1",
        status: "active",
        completed_count: 1,
        remaining_count: 2,
      },
      current_card: {
        preview_spec: {
          kind: "anki_card_preview",
          assets: [{ logicalPath: "collection.media/audio.mp3" }],
          degraded: [],
        },
        tutoring_summary: {
          prompt: "hola",
        },
        study_media: {
          audio: [
            {
              media_url: "/Users/test/.openclaw/canvas/documents/cv_test/collection.media/audio.mp3",
            },
          ],
          answer_audio: [],
          images: [],
          degraded: [],
        },
        media: {
          audio: [{ path: "/tmp/audio.mp3", exists: true, error_code: null }],
          images: [{ path: "/tmp/image.png", exists: true, error_code: null }],
        },
      },
    },
  });
  const hooks = [];
  try {
    plugin.register({
      pluginConfig: {
        ankicliPath: fake.scriptPath,
        toolMode: "llm-default",
      },
      resolvePath: (value) => value,
      registerTool() {},
      on(eventName, handler) {
        hooks.push({ eventName, handler });
      },
      logger: { warn() {} },
    });

    const hookResult = await hooks[0].handler();
    assert.match(
      hookResult.appendSystemContext,
      /active card details already include inline canvas metadata for Control UI; use current_card.tutoring_summary for reasoning instead of asking for raw preview HTML, keep details front-side only, and call anki_study_reveal before discussing answer-side content/,
    );
    assert.match(
      hookResult.appendSystemContext,
      /active card rich preview assets: 1 declared/,
    );
    assert.match(
      hookResult.appendSystemContext,
      /active card tutoring_summary is the compact reasoning surface; prefer it over raw_fields or rendered HTML unless the user explicitly asks for debug detail/,
    );
    assert.match(
      hookResult.appendSystemContext,
      /the active card remains front-side by default; call anki_study_reveal before discussing answer-side content or grading/,
    );
    assert.match(
      hookResult.appendSystemContext,
      /active card study_media contains channel-ready managed media URLs; for Discord or Telegram, send those native media assets instead of relying on the web render/,
    );
  } finally {
    fake.cleanup();
  }
});

test("before_prompt_build adds unresolved media error guidance without noisy resolved hints", async () => {
  const fake = createFakeAnkicli({
    studyDetails: {
      session: {
        id: "session-1",
        status: "active",
        completed_count: 1,
        remaining_count: 2,
      },
      current_card: {
        preview_spec: {
          kind: "anki_card_preview",
          assets: [],
          degraded: [{ errorCode: "MEDIA_FILE_MISSING" }],
        },
        tutoring_summary: {
          prompt: "hola",
        },
        media: {
          audio: [{ path: "/tmp/audio.mp3", exists: false, error_code: "MEDIA_FILE_MISSING" }],
          images: [],
        },
      },
    },
  });
  const hooks = [];
  try {
    plugin.register({
      pluginConfig: {
        ankicliPath: fake.scriptPath,
        toolMode: "llm-default",
      },
      resolvePath: (value) => value,
      registerTool() {},
      on(eventName, handler) {
        hooks.push({ eventName, handler });
      },
      logger: { warn() {} },
    });

    const hookResult = await hooks[0].handler();
    assert.match(
      hookResult.appendSystemContext,
      /active card has unresolved media; mention the structured media error code when relevant: MEDIA_FILE_MISSING/,
    );
    assert.match(
      hookResult.appendSystemContext,
      /active card rich preview has degraded assets; mention the structured error code when relevant: MEDIA_FILE_MISSING/,
    );
  } finally {
    fake.cleanup();
  }
});

test("study tool compacts preview payload, defaults revealed cards to Back, and creates a generic view handle before returning to the model", async () => {
  const fake = createFakeAnkicli();
  const registered = [];
  const createdDocuments = [];
  try {
    plugin.register({
      pluginConfig: {
        ankicliPath: fake.scriptPath,
        toolMode: "llm-default",
      },
      resolvePath: (value) => value,
      registerTool(tool, meta) {
        registered.push({ tool, meta });
      },
      createCanvasDocument(spec) {
        createdDocuments.push(spec);
        return Promise.resolve({
          id: "cv_test",
          kind: "html_bundle",
          title: "Listen to a word in a sentence",
          preferredHeight: 420,
          entryUrl: "/__openclaw__/canvas/documents/cv_test/index.html",
          assets: [
            {
              logicalPath: "collection.media/audio.mp3",
              contentType: "audio/mpeg",
              localPath: "/Users/test/.openclaw/canvas/documents/cv_test/collection.media/audio.mp3",
              url: "/__openclaw__/canvas/documents/cv_test/collection.media/audio.mp3",
            },
          ],
        });
      },
      on() {},
      logger: { warn() {} },
    });

    const studyTool = registered.find((entry) => entry.meta.name === "anki_study_start")?.tool;
    const result = await studyTool.execute("tool-call-1", {});
    const payload = JSON.parse(result.content[0].text);

    assert.equal(createdDocuments.length, 1);
    assert.equal(createdDocuments[0].kind, "html_bundle");
    assert.match(createdDocuments[0].entrypoint.value, /data-side="front" hidden/);
    assert.match(createdDocuments[0].entrypoint.value, /data-side="back">Back<\/button>/);
    assert.match(createdDocuments[0].entrypoint.value, /preview-tab is-active" data-side="back"/);
    assert.equal(payload.current_card.preview_spec, undefined);
    assert.equal(payload.current_card.prompt, undefined);
    assert.equal(payload.current_card.study_view, undefined);
    assert.deepEqual(payload.current_card.tutoring_summary, {
      template: "Listen to a word in a sentence",
      prompt: "それ",
      meaning: "that",
      reveal_state: "front_only",
      media: {
        audio_slots: 1,
        images: 0,
        degraded: [],
      },
    });
    assert.deepEqual(payload.current_card.view, {
      backend: "canvas",
      id: "cv_test",
      url: "/__openclaw__/canvas/documents/cv_test/index.html",
      title: "Listen to a word in a sentence",
      preferred_height: 420,
    });
    assert.deepEqual(payload.current_card.study_media, {
      audio: [
        {
          asset_id: "asset:collection.media/audio.mp3",
          role: "prompt_audio",
          label: "Prompt audio 1",
          logical_path: "collection.media/audio.mp3",
          content_type: "audio/mpeg",
          media_url: "/Users/test/.openclaw/canvas/documents/cv_test/collection.media/audio.mp3",
        },
      ],
      answer_audio: [],
      images: [],
      degraded: [],
    });
  } finally {
    fake.cleanup();
  }
});

test("study card details promotes the current card view to a top-level canvas payload", async () => {
  const fake = createFakeAnkicli();
  const registered = [];
  try {
    plugin.register({
      pluginConfig: {
        ankicliPath: fake.scriptPath,
        toolMode: "llm-default",
      },
      resolvePath: (value) => value,
      registerTool(tool, meta) {
        registered.push({ tool, meta });
      },
      createCanvasDocument() {
        return Promise.resolve({
          id: "cv_test",
          kind: "html_bundle",
          title: "Listen to a word in a sentence",
          preferredHeight: 420,
          entryUrl: "/__openclaw__/canvas/documents/cv_test/index.html",
          assets: [],
        });
      },
      on() {},
      logger: { warn() {} },
    });

    const studyTool = registered.find((entry) => entry.meta.name === "anki_study_card_details")?.tool;
    const result = await studyTool.execute("tool-call-2", {});
    const payload = JSON.parse(result.content[0].text);

    assert.equal(payload.kind, "canvas");
    assert.deepEqual(payload.presentation, { target: "assistant_message" });
    assert.deepEqual(payload.view, {
      backend: "canvas",
      id: "cv_test",
      url: "/__openclaw__/canvas/documents/cv_test/index.html",
      title: "Listen to a word in a sentence",
      preferred_height: 420,
    });
    assert.equal(payload.current_card.revealed, false);
    assert.equal(payload.current_card.tutoring_summary.reveal_state, "front_only");
  } finally {
    fake.cleanup();
  }
});

test("study reveal promotes the current card view to a top-level canvas payload with answer-side state", async () => {
  const fake = createFakeAnkicli();
  const registered = [];
  try {
    plugin.register({
      pluginConfig: {
        ankicliPath: fake.scriptPath,
        toolMode: "llm-default",
      },
      resolvePath: (value) => value,
      registerTool(tool, meta) {
        registered.push({ tool, meta });
      },
      createCanvasDocument() {
        return Promise.resolve({
          id: "cv_test",
          kind: "html_bundle",
          title: "Listen to a word in a sentence",
          preferredHeight: 420,
          entryUrl: "/__openclaw__/canvas/documents/cv_test/index.html",
          assets: [],
        });
      },
      on() {},
      logger: { warn() {} },
    });

    const studyTool = registered.find((entry) => entry.meta.name === "anki_study_reveal")?.tool;
    const result = await studyTool.execute("tool-call-3", {});
    const payload = JSON.parse(result.content[0].text);

    assert.equal(payload.kind, "canvas");
    assert.equal(payload.current_card.revealed, true);
    assert.equal(payload.current_card.tutoring_summary.reveal_state, "answer_revealed");
  } finally {
    fake.cleanup();
  }
});
