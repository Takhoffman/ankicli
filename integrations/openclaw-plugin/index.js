import {
  createAnkiCliTool,
  loadCatalogSync,
  runAnkicliJson,
} from "./src/ankicli-tool.js";

export default {
  id: "ankicli",
  name: "Anki CLI",
  description: "Thin OpenClaw tool adapter over ankicli --json.",
  register(api) {
    const config = api.pluginConfig ?? {};
    const toolMode =
      typeof config.toolMode === "string" && config.toolMode.trim()
        ? config.toolMode.trim()
        : "llm-default";
    const catalog = loadCatalogSync(api);
    const pluginTools = Array.isArray(catalog.plugin_tools) ? catalog.plugin_tools : [];

    for (const spec of selectToolSpecs(toolMode, pluginTools)) {
      api.registerTool(createAnkiCliTool(api, spec, catalog), { name: spec.name });
    }

    api.on("before_prompt_build", async () => {
      try {
        const envelope = await runAnkicliJson(api, ["catalog", "export"], {
          timeoutMs: 8_000,
          maxStdoutBytes: 500_000,
        });
        let studySummary = null;
        try {
          const studyEnvelope = await runAnkicliJson(api, ["study", "details"], {
            timeoutMs: 8_000,
            maxStdoutBytes: 500_000,
          });
          studySummary = studyEnvelope.data ?? null;
        } catch {
          studySummary = null;
        }
        return {
          appendSystemContext: buildDynamicPromptContext({
            toolMode,
            catalog: envelope.data ?? {},
            studySummary,
          }),
        };
      } catch (error) {
        api.logger?.warn?.(`ankicli before_prompt_build context failed: ${String(error)}`);
        return {};
      }
    });
  },
};

function selectToolSpecs(toolMode, toolSpecs) {
  if (toolMode === "passthrough-only" || toolMode === "expert-only") {
    return toolSpecs.filter((spec) => spec.surface === "expert");
  }
  if (toolMode === "curated-only" || toolMode === "legacy-low-level") {
    return toolSpecs.filter((spec) => spec.surface === "legacy");
  }
  if (toolMode === "primary-only") {
    return toolSpecs.filter((spec) => spec.surface === "primary");
  }
  if (toolMode === "llm-default") {
    return toolSpecs.filter((spec) => spec.surface !== "legacy");
  }
  return toolSpecs;
}

function buildDynamicPromptContext({ toolMode, catalog, studySummary }) {
  const supportedWorkflows = catalog.supported_workflows ?? {};
  const workflowSupport = catalog.workflow_support ?? {};
  const workflowSpecs = Array.isArray(catalog.workflows) ? catalog.workflows : [];
  const unsupportedPrimaryActions = workflowSpecs.flatMap((workflow) => {
    if (workflow.kind !== "primary") {
      return [];
    }
    const support = workflowSupport[workflow.id];
    const actionSupport = support?.actions ?? {};
    const actions = Array.isArray(workflow.actions) ? workflow.actions : [];
    const unsupported = actions
      .filter((action) => actionSupport[action.id] === false)
      .map((action) => `${workflow.id}.${action.id}`);
    return unsupported;
  });
  const supportedPrimary = workflowSpecs
    .filter((workflow) => workflow.kind === "primary" && supportedWorkflows[workflow.id] === true)
    .map((workflow) => `- ${workflow.id}: ${workflow.description}`);
  const unsupportedPrimary = workflowSpecs
    .filter((workflow) => workflow.kind === "primary" && supportedWorkflows[workflow.id] === false)
    .map((workflow) => workflow.id);
  const notes = Array.isArray(catalog.notes) ? catalog.notes : [];
  const sessionMode =
    workflowSupport["study.grade.backend"]?.supported === true
      ? "backend-write available"
      : "local-only grading";

  const lines = [
    "Anki plugin runtime context:",
    `- catalog_schema_version: ${String(catalog.schema_version ?? "unknown")}`,
    `- backend: ${String(catalog.backend ?? "unknown")}`,
    `- backend_available: ${String(catalog.available ?? "unknown")}`,
    `- tool_mode: ${toolMode}`,
    `- study_mode: ${sessionMode}`,
    "- prefer the primary workflow tools for study and management work",
    "- use the expert `ankicli` passthrough only when the primary or legacy surfaces cannot express the needed action",
  ];
  if (supportedPrimary.length > 0) {
    lines.push("- supported primary workflows:");
    lines.push(...supportedPrimary);
  }
  if (unsupportedPrimary.length > 0) {
    lines.push(`- unsupported primary workflows: ${unsupportedPrimary.join(", ")}`);
  }
  if (unsupportedPrimaryActions.length > 0) {
    lines.push(`- unsupported primary actions: ${unsupportedPrimaryActions.join(", ")}`);
  }
  if (notes.length > 0) {
    lines.push("- backend notes:");
    for (const note of notes) {
      lines.push(`- ${String(note)}`);
    }
  }
  if (studySummary?.session?.id) {
    lines.push("- active_study_session:");
    lines.push(`- session_id: ${String(studySummary.session.id)}`);
    lines.push(`- session_status: ${String(studySummary.session.status ?? "unknown")}`);
    lines.push(
      `- queue: completed=${String(studySummary.session.completed_count ?? 0)} remaining=${String(studySummary.session.remaining_count ?? 0)}`,
    );
    const renderHints = buildStudyRenderHints(studySummary.current_card);
    if (renderHints.length > 0) {
      lines.push(...renderHints);
    }
  }
  return lines.join("\n");
}

function buildStudyRenderHints(currentCard) {
  if (!currentCard || typeof currentCard !== "object") {
    return [];
  }
  const media = currentCard.media;
  const preview = currentCard.preview_spec;
  const studyMedia =
    currentCard.study_media && typeof currentCard.study_media === "object"
      ? currentCard.study_media
      : null;
  const tutoringSummary =
    currentCard.tutoring_summary &&
    typeof currentCard.tutoring_summary === "object" &&
    !Array.isArray(currentCard.tutoring_summary)
      ? currentCard.tutoring_summary
      : null;
  const lines = [];

  if (preview && typeof preview === "object" && preview.kind === "anki_card_preview") {
    const assets = Array.isArray(preview.assets) ? preview.assets : [];
    const degraded = Array.isArray(preview.degraded) ? preview.degraded : [];
    lines.push(
      "- active card details already include inline canvas metadata for Control UI; use current_card.tutoring_summary for reasoning instead of asking for raw preview HTML, keep details front-side only, and call anki_study_reveal before discussing answer-side content",
    );
    if (assets.length > 0) {
      lines.push(`- active card rich preview assets: ${String(assets.length)} declared`);
    }
    if (degraded.length > 0) {
      const errorCodes = [...new Set(degraded.map((entry) => String(entry.errorCode)).filter(Boolean))];
      if (errorCodes.length > 0) {
        lines.push(
          `- active card rich preview has degraded assets; mention the structured error code when relevant: ${errorCodes.join(", ")}`,
        );
      }
    }
  }

  if (tutoringSummary) {
    lines.push(
      "- active card tutoring_summary is the compact reasoning surface; prefer it over raw_fields or rendered HTML unless the user explicitly asks for debug detail",
    );
    lines.push(
      "- the active card remains front-side by default; call anki_study_reveal before discussing answer-side content or grading",
    );
  }

  if (studyMedia) {
    const promptAudio = Array.isArray(studyMedia.audio) ? studyMedia.audio : [];
    const answerAudio = Array.isArray(studyMedia.answer_audio) ? studyMedia.answer_audio : [];
    const images = Array.isArray(studyMedia.images) ? studyMedia.images : [];
    const degraded = Array.isArray(studyMedia.degraded) ? studyMedia.degraded : [];
    if (promptAudio.length > 0 || answerAudio.length > 0 || images.length > 0) {
      lines.push(
        "- active card study_media contains channel-ready managed media URLs; for Discord or Telegram, send those native media assets instead of relying on the web render",
      );
    }
    if (degraded.length > 0) {
      const errorCodes = [...new Set(degraded.map((entry) => String(entry.error_code)).filter(Boolean))];
      if (errorCodes.length > 0) {
        lines.push(
          `- active card study_media has degraded assets; mention the structured error code when relevant: ${errorCodes.join(", ")}`,
        );
      }
    }
  }

  if (!media || typeof media !== "object") {
    return lines;
  }

  const audio = Array.isArray(media.audio) ? media.audio : [];
  const images = Array.isArray(media.images) ? media.images : [];
  const unresolved = [...audio, ...images].filter(
    (entry) => entry?.error_code && entry?.exists !== true,
  );

  if (unresolved.length > 0) {
    const errorCodes = [...new Set(unresolved.map((entry) => String(entry.error_code)))];
    lines.push(
      `- active card has unresolved media; mention the structured media error code when relevant: ${errorCodes.join(", ")}`,
    );
  }
  return lines;
}
