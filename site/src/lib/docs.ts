import { installerScripts, platformCards, rawBaseUrl } from "./install";

export type CommandBlock = {
  label: string;
  body: string;
};

export type DocSection = {
  heading: string;
  body: string[];
  bullets?: string[];
  commands?: CommandBlock[];
};

export type DocPage = {
  title: string;
  eyebrow: string;
  summary: string;
  helper: string;
  whenToUse: string[];
  agentShouldKnow: string[];
  sections: DocSection[];
};

const verifyBlock = "ankicli --version\nankicli --json doctor env\nankicli --json doctor backend";
const cliHelpBlock =
  "ankicli --help\nankicli profile --help\nankicli search --help\nankicli note --help\nankicli backup --help\nankicli sync --help\nankicli study --help";
const publicSkillBase = `${rawBaseUrl}/skills`;

function skillUrl(skillId: string): string {
  return `${publicSkillBase}/${skillId}/SKILL.md`;
}

function codexSkillInstallBlock(skillId: string): string {
  return `mkdir -p ~/.codex/skills/${skillId}\ncurl -fsSL ${skillUrl(skillId)} -o ~/.codex/skills/${skillId}/SKILL.md`;
}

function codexSkillInstallBlockWindows(skillId: string): string {
  return `New-Item -ItemType Directory -Force \"$HOME/.codex/skills/${skillId}\" | Out-Null\nInvoke-WebRequest ${skillUrl(skillId)} -OutFile \"$HOME/.codex/skills/${skillId}/SKILL.md\"`;
}

const collectionSkillBody = `---
name: ankicli-collection-management
description: Teach the agent how to inspect and manage collection and deck state through ankicli.
---

Read first, dry-run deck writes when supported, and re-verify after mutation.

Prefer:

- \`ankicli --json ... collection info\`
- \`ankicli --json ... deck list\`
- \`ankicli --json ... deck stats --name <deck>\`
- \`ankicli --json ... search preview --kind notes --query 'deck:<deck>'\`

## Rules

1. Inspect collection and deck state before mutating.
2. Keep deck operations narrowly scoped.
3. Re-run deck or collection reads after successful writes.
4. For deck create, rename, delete, or reparent operations, use \`--dry-run\` or \`--yes\` as required and explain backend support gaps before attempting the mutation.`;

const authoringSkillBody = `---
name: ankicli-note-authoring
description: Teach the agent how to add, inspect, update, and retag notes safely through ankicli.
---

Find the target note first, validate structure mentally, and re-read after writes.

Prefer:

- \`ankicli --json ... search preview --kind notes --query ...\`
- \`ankicli --json ... note add ...\`
- \`ankicli --json ... note update ...\`
- \`ankicli --json ... note add-tags ...\`

## Rules

1. Search or inspect before mutating an existing note.
2. Use \`--dry-run\` for adds, updates, retagging, deletes, and moves when available.
3. Treat deletes and broad retagging as explicit user intent only.
4. Re-read the note or preview the target set after successful writes so the operator can verify the final state.`;

const studySkillBody = `---
name: ankicli-study
description: Teach the agent how to run tutor-style Anki study sessions through ankicli.
---

Use the primary study workflows first and keep tutoring separate from collection mutation.

Prefer:

- \`ankicli --json ... collection info\`
- \`ankicli --json ... study start ...\`
- \`ankicli --json study details\`
- \`ankicli --json study reveal\`
- \`ankicli --json study grade --rating ...\`
- \`ankicli --json study summary\`

## Rules

1. Start with the narrowest deck or query scope that matches the learner goal.
2. Use \`study details\` as the default current-card read for the front side, and use \`study reveal\` when the user asks for the answer or back side.
3. Present study cards like Anki by default: focus on the prompt and front-side clues first, and do not volunteer the answer until after \`study reveal\`.
4. Present grading choices in this order when guiding the learner: 1. Again 2. Hard 3. Good 4. Easy.
5. Treat study-session state as the tutoring source of truth unless the workflow explicitly says it writes back to Anki.
6. Explain misses in study terms and patterns instead of dumping raw database fields.

## Anti-Patterns

- Do not default to low-level note or deck mutations when the user asked to study.
- Do not skip \`study reveal\` when the user asks for the answer or when grading requires a revealed card.`;

const diagnosticsSkillBody = `---
name: ankicli-diagnostics
description: Teach the agent how to diagnose ankicli runtime, backend, collection, and capability issues.
---

Treat structured ankicli errors as authoritative and distinguish setup problems from unsupported behavior.

Prefer:

- \`ankicli --json doctor env\`
- \`ankicli --json doctor backend\`
- \`ankicli --json doctor capabilities\`
- \`ankicli --json ... collection info\`

## Rules

1. Confirm runtime, backend, and collection readiness first.
2. Differentiate missing setup from backend operation support gaps.
3. If one backend fails, check whether the alternate backend is intended and supported before retrying a write.
4. Preserve structured error codes and capability reasons verbatim instead of paraphrasing them into vague summaries.`;

const releaseSkillBody = `---
name: ankicli-release
description: Teach the agent how to prepare and validate ankicli release and packaging work.
---

Treat releases as packaging-sensitive changes. Confirm version, build, distribution tests, standalone artifacts, installer checksum behavior, and tag-triggered GitHub Release publishing before recommending a release.

Prefer:

- \`uv sync --extra dev --frozen\`
- \`uv run ruff check .\`
- \`uv run pytest -m "unit or smoke"\`
- \`uv build\`
- \`uv run pytest -m distribution\`
- \`uv run python scripts/build_release_artifact.py --target <target> --version <version>\`

## Rules

1. Start with the current version in \`pyproject.toml\` and the installed command name: the PyPI distribution is \`anki-agent-toolkit\`, while the executable is \`ankicli\`.
2. Treat \`uv.lock\` as mandatory. If dependency resolution changes, update and include the lockfile in the same release-prep change.
3. Run the smallest useful release gate first, then broaden to packaging checks: \`uv run pytest -m "unit or smoke"\`, \`uv build\`, and \`uv run pytest -m distribution\`.
4. For standalone release artifacts, use \`scripts/build_release_artifact.py\` and target only supported release IDs: \`darwin-x64\`, \`darwin-arm64\`, \`linux-x64\`, and \`windows-x64\`.
5. Verify artifact names and checksums match the contract in \`ankicli.app.releases\` before publishing or advising a manual upload.
6. Treat installer checksum mismatch, missing executable payloads, or failed distribution tests as release-blocking.
7. GitHub Releases are tag-triggered from \`v*\`; do not push a release tag or publish artifacts unless the operator explicitly asks for that release action.

## Anti-Patterns

- Do not describe an editable install, fixture integration run, or smoke test alone as proof that a release artifact is valid.
- Do not change the PyPI distribution name or executable name casually during release prep.
- Do not upload or publish artifacts when build, checksum, or distribution validation is incomplete.`;

function installCommandFor(platformId: "macos" | "linux" | "windows"): string {
  const platform = platformCards.find((item) => item.id === platformId);
  if (!platform) {
    throw new Error(`Missing install command for ${platformId}`);
  }
  return platform.installCommand;
}

export const docsPages: Record<string, DocPage> = {
  "agent-skills": {
    title: "Agent skills",
    eyebrow: "Skills",
    summary:
      "Use these standalone ankicli skills when you want the OpenClaw-style Anki skills in a public, harness-agnostic form that can be copied into Codex or another compatible skill home today.",
    helper: "Paste this page into your LLM chat or copy a specific skill file directly.",
    whenToUse: [
      "You want the existing Anki skill ideas without depending on the OpenClaw plugin bundle.",
      "You want a stable public repo path and copy-paste install flow for Codex or another compatible agent harness.",
    ],
    agentShouldKnow: [
      "These skills are generic copies of the existing OpenClaw-oriented skill concepts, rewritten around ankicli commands instead of plugin-only tool names.",
      "Humans can install one or more skills into a local skill home, then hand the docs or skill files to the agent for recurring Anki work.",
    ],
    sections: [
      {
        heading: "What this page ships",
        body: [
          "The canonical public copies live under the repo-top `skills/` folder. That makes them easy to link, curl, and copy without exposing hidden repo-local paths or waiting for the plugin release.",
          "You can install them directly into a Codex home today, or just copy the `SKILL.md` body from this page and self-create the file manually.",
        ],
        commands: [
          {
            label: "Public skill files",
            body: `skills/ankicli-collection-management/SKILL.md\nskills/ankicli-note-authoring/SKILL.md\nskills/ankicli-study/SKILL.md\nskills/ankicli-diagnostics/SKILL.md\nskills/ankicli-release/SKILL.md`,
          },
        ],
        bullets: [
          "The OpenClaw plugin copies can stay where they are for now.",
          "These top-level copies are the public source of truth for standalone install and docs.",
        ],
      },
      {
        heading: "Install ankicli-collection-management",
        body: [
          "Use this when the agent needs to inspect deck state, verify collection readiness, and keep deck mutations narrow and reversible.",
        ],
        commands: [
          { label: "Install into Codex home (macOS/Linux)", body: codexSkillInstallBlock("ankicli-collection-management") },
          { label: "Install into Codex home (Windows PowerShell)", body: codexSkillInstallBlockWindows("ankicli-collection-management") },
          { label: "SKILL.md", body: collectionSkillBody },
        ],
      },
      {
        heading: "Install ankicli-note-authoring",
        body: [
          "Use this when the agent needs to add, update, and retag notes through ankicli without skipping search, preview, or dry-run safety steps.",
        ],
        commands: [
          { label: "Install into Codex home (macOS/Linux)", body: codexSkillInstallBlock("ankicli-note-authoring") },
          { label: "Install into Codex home (Windows PowerShell)", body: codexSkillInstallBlockWindows("ankicli-note-authoring") },
          { label: "SKILL.md", body: authoringSkillBody },
        ],
      },
      {
        heading: "Install ankicli-study",
        body: [
          "Use this when the agent should behave like a tutor over ankicli study mode instead of dropping into raw note or deck mutation flows.",
        ],
        commands: [
          { label: "Install into Codex home (macOS/Linux)", body: codexSkillInstallBlock("ankicli-study") },
          { label: "Install into Codex home (Windows PowerShell)", body: codexSkillInstallBlockWindows("ankicli-study") },
          { label: "SKILL.md", body: studySkillBody },
        ],
      },
      {
        heading: "Install ankicli-diagnostics",
        body: [
          "Use this when the agent needs a debugging skill for runtime health, backend support gaps, profile targeting, and structured ankicli failures.",
        ],
        commands: [
          { label: "Install into Codex home (macOS/Linux)", body: codexSkillInstallBlock("ankicli-diagnostics") },
          { label: "Install into Codex home (Windows PowerShell)", body: codexSkillInstallBlockWindows("ankicli-diagnostics") },
          { label: "SKILL.md", body: diagnosticsSkillBody },
        ],
      },
      {
        heading: "Install ankicli-release",
        body: [
          "Use this when the agent needs to prepare release changes, validate packaging, check standalone artifacts, or reason about tag-triggered GitHub Release publishing.",
        ],
        commands: [
          { label: "Install into Codex home (macOS/Linux)", body: codexSkillInstallBlock("ankicli-release") },
          { label: "Install into Codex home (Windows PowerShell)", body: codexSkillInstallBlockWindows("ankicli-release") },
          { label: "SKILL.md", body: releaseSkillBody },
        ],
      },
      {
        heading: "How to use them",
        body: [
          "A good operator pattern is: install ankicli, verify the local runtime, install one or more of these skills into the local skill home, then hand the matching docs page or `Copy Page` output to the agent.",
          "The skills are intentionally narrow. Use the study skill for tutoring, the note-authoring skill for content changes, the collection-management skill for deck state, the diagnostics skill when the environment is suspect, and the release skill for packaging or publish readiness.",
        ],
        commands: [
          {
            label: "Operator verification baseline",
            body: 'ankicli --version\nankicli --json doctor env\nankicli --json doctor backend\nankicli --json profile list',
          },
        ],
      },
    ],
  },
  "cli-guide": {
    title: "CLI guide",
    eyebrow: "Operations",
    summary:
      "Use this page when you need the practical shape of ankicli commands: how targeting works, when to use --json, and which safety flags matter before real collection mutations.",
    helper: "Paste this page into your LLM chat for structured context.",
    whenToUse: [
      "You want a fast mental model for how ankicli commands are structured.",
      "You need exact command patterns for scripts, agent harnesses, or manual terminal use.",
    ],
    agentShouldKnow: [
      "Use `--json` by default in automation contexts.",
      "Pick one target mode first: `--profile` for normal local use or `--collection` for exact file targeting.",
    ],
    sections: [
      {
        heading: "Start with help output",
        body: [
          "The fastest way to discover the live CLI surface is still the built-in help. Use top-level help first, then narrow into the subcommand group you actually need.",
        ],
        commands: [{ label: "Help discovery", body: cliHelpBlock }],
      },
      {
        heading: "Understand the command shape",
        body: [
          "Most real commands follow the same pattern: global output and target flags first, then the subcommand group, then the concrete action and its arguments.",
          "That consistency matters because it makes the CLI easier for humans to scan and easier for agents to generate reliably.",
        ],
        commands: [
          {
            label: "Typical command shape",
            body: 'ankicli --json --profile "User 1" collection info\nankicli --json --profile "User 1" search preview --kind notes --query \'deck:Default\'\nankicli --json --profile "User 1" note update --id 123 --field Back="Updated text"',
          },
        ],
      },
      {
        heading: "Choose the right target mode",
        body: [
          "Use `--profile` when the operator has a normal local Anki setup and wants ankicli to resolve the right collection automatically.",
          "Use `--collection` when you need to hit an exact file path for debugging, test fixtures, or tightly controlled automation.",
        ],
        commands: [
          {
            label: "Targeting examples",
            body: 'ankicli --json --profile "User 1" collection info\nankicli --json --collection /path/to/collection.anki2 collection info',
          },
        ],
        bullets: [
          "Prefer `--profile` for ordinary human and operator flows.",
          "Prefer `--collection` only when exact file targeting is part of the requirement.",
        ],
      },
      {
        heading: "Use the safety flags intentionally",
        body: [
          "`--dry-run` is the default way to preview a risky mutation. `--yes` is the explicit confirmation for destructive or sensitive operations that should not happen by accident.",
        ],
        commands: [
          {
            label: "Safety patterns",
            body: 'ankicli --json --profile "User 1" note add-tags --id 123 --tag review --dry-run\nankicli --json --profile "User 1" card suspend --id 456 --yes',
          },
        ],
        bullets: [
          "Use read commands first when the target is not fully obvious.",
          "Let the human supervise the final write step when the operation is broad or destructive.",
        ],
      },
    ],
  },
  "common-tasks": {
    title: "Common tasks",
    eyebrow: "Operations",
    summary:
      "Use this page when you need exact commands for the most common ankicli workflows: inspecting collections, searching cards, changing notes, backing up, syncing, and running study sessions.",
    helper: "Paste this page into your LLM chat for structured context.",
    whenToUse: [
      "You want concrete commands rather than product-level examples.",
      "You need a task-oriented page to hand to a human operator or an agent harness.",
    ],
    agentShouldKnow: [
      "Prefer read and preview commands before mutation commands.",
      "Use backup and sync preflight steps explicitly instead of assuming remote and local state are already safe.",
    ],
    sections: [
      {
        heading: "Inspect the local environment and collection",
        body: [
          "These are the baseline read commands to confirm the local setup, find profiles, and inspect the collection before anything riskier happens.",
        ],
        commands: [
          {
            label: "Inspection baseline",
            body: 'ankicli --json profile list\nankicli --json profile default\nankicli --json --profile "User 1" collection info\nankicli --json --profile "User 1" deck list',
          },
        ],
      },
      {
        heading: "Search notes and cards safely",
        body: [
          "Use preview-style searches when a human or agent needs to inspect the target set before creating or changing anything.",
        ],
        commands: [
          {
            label: "Search and preview",
            body: 'ankicli --json --profile "User 1" search preview --kind notes --query \'deck:Default\' --limit 10\nankicli --json --profile "User 1" search preview --kind cards --query \'tag:review\' --limit 10',
          },
        ],
      },
      {
        heading: "Create or update notes",
        body: [
          "Once the deck and model are confirmed, use note mutations directly. For updates, preview the target first and use `--dry-run` where the command supports it.",
        ],
        commands: [
          {
            label: "Note mutation examples",
            body: 'ankicli --json --profile "User 1" note add --deck Default --model Basic --field Front="Question" --field Back="Answer"\nankicli --json --profile "User 1" note update --id 123 --field Back="Updated answer"\nankicli --json --profile "User 1" note add-tags --id 123 --tag review --dry-run',
          },
        ],
      },
      {
        heading: "Back up and sync explicitly",
        body: [
          "Backup and sync solve different problems. Use both intentionally instead of assuming one covers the other.",
        ],
        commands: [
          {
            label: "Backup and sync preflight",
            body: 'ankicli --json --profile "User 1" backup create\nankicli --json auth status\nankicli --json --profile "User 1" sync status\nankicli --json --profile "User 1" sync run',
          },
        ],
      },
      {
        heading: "Run a study session",
        body: [
          "Study mode is for local tutor-style flows. Use it when a human or agent wants turn-by-turn session control without writing review grades back into Anki scheduling.",
        ],
        commands: [
          {
            label: "Study session",
            body: 'ankicli --json --profile "User 1" study start --deck Default --limit 10\nankicli --json study next\nankicli --json study reveal\nankicli --json study grade --rating good',
          },
        ],
      },
    ],
  },
  "use-cases": {
    title: "Recipes",
    eyebrow: "Recipes",
    summary:
      "Use this page when you want workflow-mechanic recipes for how humans can brief an agent harness to study, generate cards, attach images or ElevenLabs-style audio, and repair an existing deck through ankicli.",
    helper: "Paste this page into your LLM chat for structured context.",
    whenToUse: [
      "You want to understand what ankicli is for beyond basic inspection commands.",
      "You are designing an agent workflow that studies, creates, updates, enriches, or repairs Anki cards.",
    ],
    agentShouldKnow: [
      "ankicli is the trusted local Anki control surface. External providers such as image models or ElevenLabs generate content, while ankicli validates targets and performs the actual note, media, backup, and sync operations.",
      "Humans usually install, verify, and approve high-risk changes. Agents orchestrate the repeated retrieval, generation, and mutation workflows after the environment is healthy.",
    ],
    sections: [
      {
        heading: "Recipe 1: Study copilot with error tracking",
        body: [
          "This is the simplest high-value operator flow. A human scopes the session, then the agent handles turn-taking, reveal timing, weak-card tracking, and an end-of-session summary.",
          "Use this when you want a tutor-style conversation without pretending the CLI is the Anki desktop review screen.",
        ],
        commands: [
          {
            label: "Prompt for Claude, Codex, or OpenClaw",
            body: 'Use ankicli to run a 20-card study session from my Spanish deck.\nReveal the answer only after I respond.\nTrack cards I miss, explain the mistake briefly, and summarize weak areas at the end.\nUse --json for every ankicli command.',
          },
          {
            label: "ankicli flow",
            body: 'ankicli --json --profile "User 1" study start --deck Spanish --limit 20\nankicli --json study next\nankicli --json study reveal\nankicli --json study grade --rating again\nankicli --json study summary',
          },
        ],
        bullets: [
          "Use this for language decks, interview prep decks, or any deck where the agent should explain mistakes after each reveal.",
          "Keep in mind that study mode is local session state, not a direct write into Anki review scheduling.",
        ],
      },
      {
        heading: "Recipe 2: Turn notes into atomic cards",
        body: [
          "A strong creation flow is: human provides notes or a topic, the agent turns them into atomic cards, and ankicli performs the validated deck/model lookup plus note creation.",
          "This is better than a blind bulk import because the agent can rewrite broad material into concise front/back pairs before ankicli touches the collection.",
        ],
        commands: [
          {
            label: "Prompt for Claude, Codex, or OpenClaw",
            body: 'Take these biology notes and draft good atomic flashcards.\nAvoid duplicates, keep each card answerable in one step, and put the final cards in my Biology deck.\nShow me the proposed fronts and backs first, then create them with ankicli after I approve.',
          },
          {
            label: "ankicli flow",
            body: 'ankicli --json model list\nankicli --json deck list\nankicli --json --profile "User 1" note add --deck Biology --model Basic --field Front="What does the mitochondrion do?" --field Back="It produces ATP for the cell."',
          },
        ],
        bullets: [
          "Use this for notes-to-cards, lecture-to-cards, or article-to-cards pipelines.",
          "The agent should usually draft first and then create the notes only after the deck, model, and card quality are confirmed.",
        ],
      },
      {
        heading: "Recipe 3: Create image-backed vocabulary cards",
        body: [
          "ankicli becomes much more interesting when an external image provider generates the media and ankicli handles the note and collection side safely.",
          "A good example is vocabulary training: the agent chooses a word list, generates educational image prompts, saves the images, and then creates or updates cards that reference those media files.",
        ],
        commands: [
          {
            label: "Prompt for Claude, Codex, or OpenClaw",
            body: 'Create 15 beginner Japanese noun cards in my "Japanese Core" deck.\nFor each word, generate one clear educational image with my image provider.\nPut the image on the back of the card, keep the text concise, and verify the created notes with ankicli when finished.',
          },
          {
            label: "Image prompt pattern",
            body: 'Word: りんご\nPrompt: "Simple educational illustration of a red apple on a plain light background, high clarity, flashcard-friendly, no text overlay"',
          },
          {
            label: "ankicli flow",
            body: 'ankicli --json --profile "User 1" search preview --kind notes --query \'deck:"Japanese Core" note:Basic\' --limit 10\nankicli --json --profile "User 1" note update --id 123 --field Back="<img src=\\"apple.png\\">\\nA red apple."',
          },
        ],
        bullets: [
          "Best fit: vocabulary, anatomy, geography, object recognition, and children’s language decks.",
          "Keep the image prompt educational and flashcard-friendly rather than photorealistic for its own sake.",
        ],
      },
      {
        heading: "Recipe 4: Fill missing pronunciation audio with ElevenLabs-style TTS",
        body: [
          "Text-to-speech providers like ElevenLabs fit naturally into a media-enrichment workflow. The agent can search for cards missing audio, generate pronunciation files, and then update the note fields with `[sound:...]` references.",
          "This is especially strong for language decks where humans want consistent pronunciation, listening drills, or sentence audio without recording every file manually.",
        ],
        commands: [
          {
            label: "Prompt for Claude, Codex, or OpenClaw",
            body: 'Find French cards in my collection that are missing pronunciation audio.\nUse ElevenLabs to generate native-sounding audio only for missing items.\nAttach the audio to the card, avoid duplicates, and mark updated notes so I can review them later.',
          },
          {
            label: "ankicli flow",
            body: 'ankicli --json --profile "User 1" search preview --kind notes --query \'deck:French "Bonjour"\' --limit 5\nankicli --json --profile "User 1" note update --id 456 --field Back="[sound:bonjour-elevenlabs.mp3]\\nHello"',
          },
          {
            label: "Optional tagging for review",
            body: 'ankicli --json --profile "User 1" note add-tags --id 456 --tag audio-generated --dry-run\nankicli --json --profile "User 1" note add-tags --id 456 --tag audio-generated --yes',
          },
        ],
        bullets: [
          "Use one voice for prompt-side pronunciation and another only if you intentionally want contrast or translation audio.",
          "The agent should deduplicate audio generation rather than recreating files each run.",
        ],
      },
      {
        heading: "Recipe 5: Build a polished multimodal deck",
        body: [
          "The highest-leverage workflow combines LLM drafting, image generation, and TTS. The agent builds a polished note package, while ankicli remains the safe local write layer.",
          "A typical pipeline is: take a word list or notes, generate concise card text, create an image prompt, synthesize audio, then create the note with all media linked correctly.",
        ],
        commands: [
          {
            label: "Prompt for Claude, Codex, or OpenClaw",
            body: 'Make me a polished deck for 50 beginner Italian nouns.\nEach card should include the Italian word, an English gloss, a generated image, ElevenLabs pronunciation audio, and one simple example sentence.\nShow me 5 sample cards first, then create the rest after I approve.',
          },
          {
            label: "ankicli flow",
            body: 'ankicli --json --profile "User 1" note add --deck Italian --model Basic --field Front="la mela" --field Back="<img src=\\"la-mela.png\\">\\n[sound:la-mela.mp3]\\nThe apple"\nankicli --json --profile "User 1" search preview --kind notes --query \'deck:Italian "la mela"\' --limit 3',
          },
        ],
        bullets: [
          "This is the clearest flagship use case for image + TTS providers around ankicli.",
          "It turns ankicli into the reliable Anki mutation layer inside an agent-built learning workflow.",
        ],
      },
      {
        heading: "Recipe 6: Repair and upgrade an existing deck",
        body: [
          "Not every valuable workflow is about new content. ankicli is also a good repair surface for agents that find missing audio, poor tags, verbose cards, duplicate notes, or cards that should be split into smaller units.",
          "These flows are practical because an agent can audit the collection, propose targeted fixes, and then apply them through dry-run-first note and card commands instead of brittle UI automation.",
        ],
        commands: [
          {
            label: "Prompt for Claude, Codex, or OpenClaw",
            body: 'Audit my Spanish deck for cards that are too verbose, duplicated, poorly tagged, or missing audio.\nShow me a repair plan first.\nThen apply only the approved fixes with ankicli, using dry-run where possible and tagging touched notes for review.',
          },
          {
            label: "ankicli flow",
            body: 'ankicli --json --profile "User 1" search preview --kind notes --query \'deck:Spanish tag:needs-audio\' --limit 20\nankicli --json --profile "User 1" note add-tags --id 789 --tag audio-generated --dry-run',
          },
        ],
        bullets: [
          "Good targets: missing media, leech cleanup, tag normalization, deck moves, and card wording refactors.",
          "Use `--dry-run` first when the agent is making structural cleanup decisions.",
        ],
      },
      {
        heading: "Recipe 7: Build a deck from source material",
        body: [
          "A strong end-to-end workflow is: give the agent source material, have it extract testable concepts, draft cards, and then create the approved notes with ankicli.",
          "This is a better fit than hand-authoring every card when you have lecture notes, article notes, transcripts, or a chapter outline and want a fast first pass.",
        ],
        commands: [
          {
            label: "Prompt for Claude, Codex, or OpenClaw",
            body: 'Turn these lecture notes into a new study deck.\nExtract the most testable facts, keep cards atomic, avoid duplicates, and group related cards with sensible tags.\nShow me a proposed set first, then create the approved cards with ankicli.',
          },
          {
            label: "ankicli flow",
            body: 'ankicli --json deck list\nankicli --json model list\nankicli --json --profile "User 1" note add --deck "History 201" --model Basic --field Front="Question" --field Back="Answer"',
          },
        ],
        bullets: [
          "Best fit: lecture notes, article summaries, transcripts, textbook chapters, and interview prep packets.",
          "Keep a human approval step before bulk creation if the source material is long or nuanced.",
        ],
      },
      {
        heading: "Recipe 8: Draft cards first, then review before creation",
        body: [
          "Sometimes the right workflow is not immediate mutation. The agent drafts cards, the human reviews the proposal, and only then does ankicli create the accepted notes.",
          "This is especially useful when deck quality matters more than speed or when the source material is subtle enough that a human wants to inspect the proposed cards first.",
        ],
        commands: [
          {
            label: "Prompt for Claude, Codex, or OpenClaw",
            body: 'Draft 30 flashcards from these notes but do not create them yet.\nShow me the fronts, backs, tags, and target deck first.\nAfter I approve the set, create the approved cards with ankicli and tag them needs-review.',
          },
          {
            label: "ankicli flow",
            body: 'ankicli --json deck list\nankicli --json --profile "User 1" note add --deck Default --model Basic --field Front="Approved front" --field Back="Approved back"\nankicli --json --profile "User 1" note add-tags --id 123 --tag needs-review',
          },
        ],
        bullets: [
          "This is one of the safest high-autonomy authoring workflows.",
          "It works well for serious learners who want agent speed without losing editorial control.",
        ],
      },
      {
        heading: "Recipe 9: Ongoing deck maintenance automation",
        body: [
          "Some of the best uses of ankicli are recurring maintenance jobs rather than one-shot prompts. A human defines the policy once, and an agent periodically applies it through safe reads and targeted writes.",
          "Examples include filling missing audio, creating backups, reviewing leeches, or tagging cards that need attention.",
        ],
        commands: [
          {
            label: "Prompt for Claude, Codex, or OpenClaw",
            body: 'Review my Spanish deck for missing audio and badly tagged notes.\nCreate a backup first, then generate a short repair plan.\nApply only the low-risk fixes automatically, and tag anything ambiguous for manual review.',
          },
          {
            label: "ankicli flow",
            body: 'ankicli --json --profile "User 1" backup create\nankicli --json --profile "User 1" search preview --kind notes --query \'deck:Spanish -tag:audio-generated\' --limit 25\nankicli --json --profile "User 1" note add-tags --id 789 --tag needs-review --dry-run',
          },
        ],
        bullets: [
          "Best fit: recurring cleanup, media completion, and supervised maintenance workflows.",
          "Keep low-risk fixes automatic and high-risk changes reviewable.",
        ],
      },
      {
        heading: "General pattern for all recipes",
        body: [
          "The stable pattern is: a human installs and verifies ankicli, the human gives the agent a specific goal and guardrails, external providers generate optional media, and ankicli performs the collection reads and writes.",
          "This is the product shape to preserve. ankicli should remain the trusted retrieval and mutation layer, while the agent and external providers handle content generation and orchestration.",
        ],
        commands: [
          {
            label: "Operator baseline before any recipe",
            body: 'ankicli --version\nankicli --json doctor env\nankicli --json doctor backend\nankicli --json profile list',
          },
        ],
        bullets: [
          "Use `--json` consistently for agent-driven workflows.",
          "For risky mutations, prefer a human approval step before the final create or update commands run.",
        ],
      },
    ],
  },
  "learning-plans": {
    title: "Learning plans",
    eyebrow: "Planning",
    summary:
      "Use this page when the real goal is not just card creation but learning optimization: reach a deadline, prepare for a show, a trip, or an exam, and use what you already know to focus on the highest-value material.",
    helper: "Paste this page into your LLM chat for structured context.",
    whenToUse: [
      "You have a real-world goal like travel, anime immersion, or an exam and want the agent to optimize study around it.",
      "You want ankicli to support a time-bounded plan rather than just a one-off card generation task.",
    ],
    agentShouldKnow: [
      "These plans should take current deck coverage, obvious weak areas, and a fixed time budget into account before adding new material.",
      "The best plans are adaptive: inspect what the learner already knows, prioritize high-payoff gaps, and avoid flooding the deck with low-value content.",
    ],
    sections: [
      {
        heading: "Plan 1: Prepare for Japan in 90 days",
        body: [
          "This is a deadline-driven travel workflow. The agent should optimize for practical spoken usefulness, not abstract coverage of the whole language.",
          "A good plan prioritizes survival phrases, restaurants, transit, hotels, emergencies, and politeness, then adapts new cards to what the learner already knows.",
        ],
        commands: [
          {
            label: "Prompt for Claude, Codex, or OpenClaw",
            body: 'I am traveling to Japan in 3 months.\nI have 1 hour a day.\nUse my existing decks and what I already seem to know to build the most useful study plan possible.\nPrioritize speaking and travel survival language.\nAdd missing cards only when they are high value.',
          },
          {
            label: "ankicli planning baseline",
            body: 'ankicli --json profile list\nankicli --json --profile "User 1" collection info\nankicli --json --profile "User 1" search preview --kind notes --query \'deck:Japanese\' --limit 25\nankicli --json --profile "User 1" study start --deck Japanese --limit 20',
          },
        ],
        bullets: [
          "Think in weeks, not just cards: transport week, food week, hotel week, emergency week.",
          "Prefer high-utility phrases over encyclopedic coverage.",
        ],
      },
      {
        heading: "Plan 2: Study toward a specific anime",
        body: [
          "This workflow is for immersion around a specific show. The agent should bias toward vocabulary, phrases, and patterns likely to be common in that show, then compare that against existing deck coverage.",
          "The interesting part is source-aware prioritization: teach the learner the words most likely to unlock comprehension for that actual media target.",
        ],
        commands: [
          {
            label: "Prompt for Claude, Codex, or OpenClaw",
            body: 'I want to watch this anime with less subtitle dependence.\nFigure out what vocabulary and patterns are common in it.\nCompare that against what I already know.\nMake me a study plan and update my deck with only the highest-value missing items.\nI can study 45 minutes a day.',
          },
          {
            label: "ankicli planning baseline",
            body: 'ankicli --json --profile "User 1" search preview --kind notes --query \'deck:Japanese tag:anime\' --limit 25\nankicli --json --profile "User 1" note add-tags --id 123 --tag anime-focus --dry-run\nankicli --json --profile "User 1" study start --deck Japanese --limit 15',
          },
        ],
        bullets: [
          "A good loop is pre-watch prep, post-watch reinforcement, then selective new-card creation.",
          "Only high-value missing items should become permanent cards.",
        ],
      },
      {
        heading: "Plan 3: Build a medical exam ramp plan",
        body: [
          "Medical students are a strong fit for goal-driven ankicli workflows because the target is usually concrete: a practical, block exam, shelf, or anatomy checkoff with a deadline.",
          "The agent should focus on likely testable structures, common confusions, image-heavy recall, and weak areas already visible in the learner’s existing deck.",
        ],
        commands: [
          {
            label: "Prompt for Claude, Codex, or OpenClaw",
            body: 'I have an anatomy practical in 6 weeks.\nUse my existing deck to identify weak areas.\nPrioritize image-based structures and commonly confused regions.\nBuild a daily 90-minute study plan.\nAdd or revise only the cards that will give the highest exam payoff.',
          },
          {
            label: "ankicli planning baseline",
            body: 'ankicli --json --profile "User 1" search preview --kind notes --query \'deck:Anatomy\' --limit 25\nankicli --json --profile "User 1" search preview --kind cards --query \'deck:Anatomy tag:weak\' --limit 25\nankicli --json --profile "User 1" note update --id 456 --field Back="<img src=\\"brachial-plexus.png\\">\\nBrachial plexus branches"',
          },
        ],
        bullets: [
          "Best fit: anatomy, pathology, pharm, and any exam with a bounded content map and obvious high-yield material.",
          "Image-heavy additions are especially useful for anatomy and practical-style exams.",
        ],
      },
      {
        heading: "Plan 4: Use my hour a day intelligently",
        body: [
          "This is the adaptive daily-coach version of the product. The agent should allocate limited time across review, new material, and weak-area reinforcement based on a real time budget.",
          "This is more valuable than static card generation because it turns ankicli into a study optimizer instead of just a card editor.",
        ],
        commands: [
          {
            label: "Prompt for Claude, Codex, or OpenClaw",
            body: 'I have 1 hour a day to study.\nDecide what I should work on each day based on what I already know, what I keep missing, my deadline, and the likely payoff of new cards versus review.\nDo not waste time on low-value repetition.',
          },
          {
            label: "ankicli planning baseline",
            body: 'ankicli --json --profile "User 1" study start --deck Default --limit 20\nankicli --json study summary\nankicli --json --profile "User 1" search preview --kind cards --query \'tag:weak\' --limit 25',
          },
        ],
        bullets: [
          "This is the best fit when the learner has limited time and needs prioritization more than raw content generation.",
          "The output should feel like a daily plan, not just a pile of new cards.",
        ],
      },
      {
        heading: "Plan 5: Optimize around what I already know",
        body: [
          "This is the deck-optimization version of planning. The agent inspects existing deck coverage, identifies weak areas and redundancy, then decides what to add, what to keep emphasizing, and what not to waste time on.",
          "It is especially useful when the learner already has a large deck and the problem is prioritization, not blank-slate content creation.",
        ],
        commands: [
          {
            label: "Prompt for Claude, Codex, or OpenClaw",
            body: 'Look at my current Japanese decks.\nFigure out what I already know well, what I keep missing, and what high-value gaps still exist.\nReorganize my next 30 days of study for maximum progress.\nSuspend or deprioritize low-value repetition and add only the most useful missing material.',
          },
          {
            label: "ankicli planning baseline",
            body: 'ankicli --json --profile "User 1" collection info\nankicli --json --profile "User 1" search preview --kind notes --query \'deck:Japanese\' --limit 50\nankicli --json --profile "User 1" note add-tags --id 789 --tag high-priority --dry-run',
          },
        ],
        bullets: [
          "This is ideal for advanced learners who already have a lot of material but want better prioritization.",
          "The key is gap analysis plus daily-plan design, not mass new-card creation.",
        ],
      },
      {
        heading: "General pattern for learning plans",
        body: [
          "A good learning plan starts with a real goal, a deadline, and a time budget. The agent then uses ankicli to inspect current deck state, identify useful gaps, and support a plan that changes over time.",
          "This is the layer where ankicli becomes more than a card tool. It becomes the safe stateful study backend for a goal-aware learning system.",
        ],
        commands: [
          {
            label: "Operator baseline before any plan",
            body: 'ankicli --version\nankicli --json doctor env\nankicli --json doctor backend\nankicli --json profile list\nankicli --json --profile "User 1" collection info',
          },
        ],
        bullets: [
          "Start with what the learner already knows, not just what they want to know.",
          "Optimize for payoff under the actual time budget.",
        ],
      },
    ],
  },
  quickstart: {
    title: "Quickstart",
    eyebrow: "Docs",
    summary:
      "Use this when you want to install ankicli, confirm the runtime is healthy, and hand a real Anki profile or collection path to an agent without guessing.",
    helper: "Paste this page into your LLM chat for structured context.",
    whenToUse: [
      "You have installed ankicli and want the fastest safe verification path.",
      "You are about to point Claude, Codex, OpenClaw, or a script at your Anki environment.",
    ],
    agentShouldKnow: [
      "ankicli is JSON-first and should usually be called with --json in automation contexts.",
      "Humans normally handle install and initial verification. Agents handle the day-to-day commands after the environment is confirmed healthy.",
    ],
    sections: [
      {
        heading: "Install first",
        body: [
          "Use the one-command installer for your platform. The script downloads a standalone GitHub Release artifact, verifies checksums, and installs ankicli into a user-local path.",
        ],
        commands: [
          { label: "macOS/Linux", body: `curl -fsSL ${installerScripts.shell} | sh` },
          { label: "Windows", body: `irm ${installerScripts.powershell} | iex` },
        ],
      },
      {
        heading: "Verify the runtime",
        body: [
          "Run these commands before giving ankicli to an agent. They confirm the executable works, the packaged runtime is healthy, and the local environment can be inspected safely.",
        ],
        commands: [{ label: "Verification", body: verifyBlock }],
      },
      {
        heading: "First safe collection checks",
        body: [
          "After verification, inspect the available profiles and resolve the one you actually want. Prefer profile-aware commands for normal local use.",
        ],
        commands: [
          {
            label: "Profile-aware flow",
            body: 'ankicli --json profile list\nankicli --json profile default\nankicli --json --profile "User 1" collection info',
          },
        ],
      },
    ],
  },
  "profiles-and-collections": {
    title: "Profiles and collections",
    eyebrow: "Docs",
    summary:
      "Use profiles for the normal human path and explicit collection paths when you need deterministic low-level targeting for automation or troubleshooting.",
    helper: "Paste this page into your LLM chat for structured context.",
    whenToUse: [
      "You want to point ankicli at the correct local Anki data without guessing where the collection lives.",
      "You need to choose between --profile and --collection in a script or agent workflow.",
    ],
    agentShouldKnow: [
      "Use --profile for ordinary local-user flows. Use --collection only when exact file targeting matters.",
      "Profile resolution is platform-aware and is safer than hard-coding Anki paths when the operator has a normal local setup.",
    ],
    sections: [
      {
        heading: "Use profiles by default",
        body: [
          "For most humans, profile-aware commands are the best fit because they map cleanly to the Anki app’s own data model.",
        ],
        commands: [
          {
            label: "Profile inspection",
            body: 'ankicli --json profile list\nankicli --json profile default\nankicli --json profile resolve --name "User 1"',
          },
        ],
      },
      {
        heading: "Use collection paths when you need exactness",
        body: [
          "Use explicit collection paths when debugging, testing, or automating against a known file path rather than a named Anki profile.",
        ],
        commands: [
          {
            label: "Collection-targeted inspection",
            body: "ankicli --json --collection /path/to/collection.anki2 collection info\nankicli --json --collection /path/to/collection.anki2 deck stats --name Default",
          },
        ],
      },
      {
        heading: "Troubleshooting hints",
        body: ["If a profile does not resolve, inspect the profile list and the resolved data root before assuming the collection is missing."],
        bullets: [
          "Run `ankicli --json doctor env` to inspect the default Anki root.",
          "Use `profile list` before hard-coding a collection path.",
        ],
      },
    ],
  },
  "sync-and-backups": {
    title: "Sync and backups",
    eyebrow: "Docs",
    summary:
      "Sync and backups solve different problems. Sync coordinates local and remote state; backups are the rollback path when a human or agent makes a mistake.",
    helper: "Paste this page into your LLM chat for structured context.",
    whenToUse: [
      "You want to confirm credentials and backend readiness before a real sync.",
      "You want a local recovery path before risky mutations or explicit restore work.",
    ],
    agentShouldKnow: [
      "Use `sync status` as the preflight step before `sync run`.",
      "Never treat sync as a replacement for backups; backup creation and restore are local safety workflows.",
    ],
    sections: [
      {
        heading: "Check auth and sync readiness first",
        body: ["Start with auth status and sync status before assuming remote state is safe to touch."],
        commands: [
          {
            label: "Sync preflight",
            body: 'ankicli --json auth status\nankicli --json --profile "User 1" sync status',
          },
        ],
      },
      {
        heading: "Backups are the rollback tool",
        body: ["Use backup commands before risky operations or whenever a human wants a straightforward local recovery point."],
        commands: [
          {
            label: "Local backup flow",
            body: 'ankicli --json --profile "User 1" backup status\nankicli --json --profile "User 1" backup list\nankicli --json --profile "User 1" backup create',
          },
        ],
      },
      {
        heading: "Caveats",
        body: ["The sync backend is standalone for python-anki. Credentials are stored locally through the supported credential store on each platform."],
        bullets: [
          "Use `sync pull` and `sync push` only when you explicitly want expert-level direction control.",
          "Use `backup restore` only when the operator clearly intends a local rollback and understands the safety implications.",
        ],
      },
    ],
  },
  study: {
    title: "Study mode",
    eyebrow: "Docs",
    summary:
      "Study mode gives you local tutor-style sessions over your collection without pretending the CLI is a full-screen study app.",
    helper: "Paste this page into your LLM chat for structured context.",
    whenToUse: [
      "You want an agent or script to drive lightweight study sessions through the terminal.",
      "You want a local study layer without mutating Anki review state.",
    ],
    agentShouldKnow: [
      "Study sessions are local state layered on collection reads. They do not write review grades back into Anki scheduling.",
      "The agent should explicitly reveal before grading and should not assume the CLI mirrors the Anki desktop review screen.",
    ],
    sections: [
      {
        heading: "Start a session",
        body: ["Scope the session to a deck or query first so the operator can see exactly what the session is about."],
        commands: [
          {
            label: "Start and progress",
            body: 'ankicli --json --profile "User 1" study start --deck Default\nankicli --json study next\nankicli --json study details',
          },
        ],
      },
      {
        heading: "Reveal, then grade",
        body: ["Reveal the answer before grading. This keeps the flow explicit and easier to supervise."],
        commands: [
          {
            label: "Reveal and grade",
            body: "ankicli --json study reveal\nankicli --json study grade --rating good\nankicli --json study summary",
          },
        ],
      },
      {
        heading: "Caveats",
        body: ["Study mode is intentionally local and lightweight."],
        bullets: [
          "Do not treat `study grade` as an Anki scheduling mutation.",
          "Use normal note/card commands when you want actual collection changes.",
        ],
      },
    ],
  },
  troubleshooting: {
    title: "Troubleshooting",
    eyebrow: "Docs",
    summary:
      "When ankicli fails, start by validating the runtime, backend support, and profile resolution instead of guessing which layer broke.",
    helper: "Paste this page into your LLM chat for structured context.",
    whenToUse: [
      "Install completed but commands still fail.",
      "An agent reports backend unavailable, runtime mismatch, or profile resolution errors.",
    ],
    agentShouldKnow: [
      "Start with `doctor env` and `doctor backend` before retrying mutations.",
      "Treat structured ankicli errors as real signals. Do not collapse them into vague summaries.",
    ],
    sections: [
      {
        heading: "Check the environment first",
        body: ["These commands surface runtime health, default Anki roots, backend support, and capability gaps."],
        commands: [
          {
            label: "Diagnostic baseline",
            body: "ankicli --json doctor env\nankicli --json doctor backend\nankicli --json doctor capabilities",
          },
        ],
      },
      {
        heading: "If install or startup fails",
        body: ["A healthy install still needs a healthy runtime. If the binary launches but commands fail, start with the doctor commands before retrying the installer."],
        commands: [
          {
            label: "Install troubleshooting",
            body: "ankicli --version\nankicli --json doctor env\nankicli --json doctor backend",
          },
        ],
        bullets: [
          "If the command is not found, fix PATH before debugging the backend.",
          "If `doctor backend` reports unsupported runtime, treat that as a runtime or setup problem, not a collection problem.",
        ],
      },
      {
        heading: "Check profile resolution and target selection",
        body: ["If a collection command fails, confirm the selected profile or collection path before blaming the backend."],
        commands: [
          {
            label: "Profile troubleshooting",
            body: 'ankicli --json profile list\nankicli --json profile resolve --name "User 1"\nankicli --json --profile "User 1" collection info',
          },
        ],
      },
      {
        heading: "Check auth and sync separately",
        body: ["If sync behavior is wrong, separate credential problems from collection problems. Start with auth status and sync status before a real sync run."],
        commands: [
          {
            label: "Auth and sync troubleshooting",
            body: 'ankicli --json auth status\nankicli --json --profile "User 1" sync status\nankicli --json --profile "User 1" backup create',
          },
        ],
        bullets: [
          "Treat sync as coordination, not backup.",
          "Create a backup before retrying a risky sync path after a failure.",
        ],
      },
      {
        heading: "Common failure modes",
        body: ["Most failures cluster around runtime health, credential state, or target selection."],
        bullets: [
          "If runtime support is false, inspect the bundled runtime version and failure reason from `doctor backend`.",
          "If auth fails, check `auth status` before retrying sync commands.",
          "If a mutation is blocked, try `--dry-run` first and verify the target with a read command.",
        ],
      },
    ],
  },
  "install-index": {
    title: "Install ankicli",
    eyebrow: "Install",
    summary:
      "Use the one-command installer for your platform when you want a stable standalone binary path without asking a human to manage Python packaging directly.",
    helper: "Paste this page into your LLM chat for structured context.",
    whenToUse: [
      "You want the recommended install path for a human operator.",
      "You want a consistent command to paste into docs, onboarding notes, or an LLM chat.",
    ],
    agentShouldKnow: [
      "Humans should usually install ankicli through the first-party script and verify it before handing the environment to an agent.",
      "The installer targets GitHub Releases artifacts and verifies checksums before install.",
    ],
    sections: [
      {
        heading: "Primary install commands",
        body: ["Choose the platform-appropriate command below. The script installs to a user-local path and runs a post-install backend check."],
        commands: platformCards.map((platform) => ({
          label: platform.label,
          body: platform.installCommand,
        })),
      },
      {
        heading: "Fallback path",
        body: [
          "If you explicitly want the Python package path instead of the standalone artifact path, use pipx.",
          "The PyPI distribution is `anki-agent-toolkit`; the installed command is still `ankicli`.",
        ],
        commands: [{ label: "Fallback", body: "pipx install anki-agent-toolkit" }],
      },
      {
        heading: "Verify after install",
        body: ["Always run the verification commands before using ankicli from an agent harness."],
        commands: [{ label: "Verification", body: verifyBlock }],
      },
      {
        heading: "If the installer fails",
        body: [
          "Do not guess. Check the local runtime and backend state directly, then decide whether the issue is download-related, PATH-related, or backend-related.",
        ],
        commands: [
          {
            label: "Install recovery baseline",
            body: "ankicli --version\nankicli --json doctor env\nankicli --json doctor backend\nankicli --json doctor capabilities",
          },
        ],
        bullets: [
          "Confirm the machine can reach GitHub Releases and raw GitHub content.",
          "If the binary is installed but not found, add the printed user-local install directory to PATH and retry.",
          "If the standalone installer path is blocked, use `pipx install anki-agent-toolkit` as the fallback path.",
        ],
      },
    ],
  },
  "install-macos": {
    title: "Install ankicli on macOS",
    eyebrow: "Install",
    summary:
      "Use the macOS installer when a human operator wants a self-contained ankicli binary for Apple Silicon or Intel without configuring Python packaging by hand.",
    helper: "Paste this page into your LLM chat for structured context.",
    whenToUse: ["You are installing ankicli on macOS and want the primary supported path."],
    agentShouldKnow: [
      "The shell installer auto-detects the correct macOS release artifact.",
      "After install, agents should still use `--json` and rely on doctor commands before real work.",
    ],
    sections: [
      {
        heading: "Install",
        body: ["Run the shell installer and then verify the backend."],
        commands: [
          { label: "Install", body: installCommandFor("macos") },
          { label: "Verify", body: "ankicli --version\nankicli --json doctor backend" },
        ],
      },
      {
        heading: "Notes",
        body: ["The installer places ankicli in a user-local path and prints a PATH hint when needed."],
        bullets: [
          "Use the standalone installer path unless you explicitly need pipx.",
          "Use profile-aware commands first after install.",
        ],
      },
    ],
  },
  "install-linux": {
    title: "Install ankicli on Linux",
    eyebrow: "Install",
    summary:
      "Use the Linux installer when a human operator wants the primary standalone ankicli path on Linux x64 with checksum verification and no system-wide package mutation.",
    helper: "Paste this page into your LLM chat for structured context.",
    whenToUse: ["You are installing ankicli on Linux x64 and want the primary supported path."],
    agentShouldKnow: [
      "The shell installer targets the Linux x64 release artifact and installs to a user-local path.",
      "Agents should still validate runtime health with doctor commands before real collection work.",
    ],
    sections: [
      {
        heading: "Install",
        body: ["Run the shell installer and then verify the backend."],
        commands: [
          { label: "Install", body: installCommandFor("linux") },
          { label: "Verify", body: "ankicli --version\nankicli --json doctor backend" },
        ],
      },
      {
        heading: "Notes",
        body: ["The installer avoids `sudo` and prints PATH guidance when the operator needs to add the binary directory manually."],
        bullets: [
          "Treat checksum mismatch as a release-blocking problem.",
          "Keep `pipx install anki-agent-toolkit` as fallback, not the default path.",
        ],
      },
    ],
  },
  "install-windows": {
    title: "Install ankicli on Windows",
    eyebrow: "Install",
    summary:
      "Use the PowerShell installer when a human operator wants the primary standalone ankicli path on Windows x64 without manually assembling Python tooling.",
    helper: "Paste this page into your LLM chat for structured context.",
    whenToUse: ["You are installing ankicli on Windows x64 and want the primary supported path."],
    agentShouldKnow: [
      "The PowerShell installer downloads the Windows standalone ZIP, verifies checksums, and installs into a user-local directory.",
      "Agents should treat the operator as responsible for first-run install and PATH confirmation.",
    ],
    sections: [
      {
        heading: "Install",
        body: ["Run the PowerShell installer and then verify the backend."],
        commands: [
          { label: "Install", body: installCommandFor("windows") },
          { label: "Verify", body: "ankicli --version\nankicli --json doctor backend" },
        ],
      },
      {
        heading: "Notes",
        body: ["The installer prints the local install directory so the operator can add it to PATH if needed."],
        bullets: [
          "Use the one-command installer for the primary path.",
          "Keep pipx as the explicit fallback, not the first recommendation.",
        ],
      },
    ],
  },
};

export function pageMarkdown(page: DocPage): string {
  const lines: string[] = [`# ${page.title}`, "", page.summary, "", "## When To Use"];

  for (const item of page.whenToUse) {
    lines.push(`- ${item}`);
  }

  lines.push("", "## What The Agent Should Know");
  for (const item of page.agentShouldKnow) {
    lines.push(`- ${item}`);
  }

  for (const section of page.sections) {
    lines.push("", `## ${section.heading}`);
    for (const paragraph of section.body) {
      lines.push("", paragraph);
    }
    if (section.bullets) {
      lines.push("");
      for (const bullet of section.bullets) {
        lines.push(`- ${bullet}`);
      }
    }
    if (section.commands) {
      for (const command of section.commands) {
        lines.push("", `### ${command.label}`, "", "```bash", command.body, "```");
      }
    }
  }

  return lines.join("\n");
}
