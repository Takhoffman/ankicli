import { createAnkiCliTool, toolSpecs } from "./src/ankicli-tool.js";

export default {
  id: "ankicli",
  name: "Anki CLI",
  description: "Thin OpenClaw tool adapter over ankicli --json.",
  register(api) {
    for (const spec of toolSpecs) {
      api.registerTool(createAnkiCliTool(api, spec), { name: spec.name });
    }
  },
};
