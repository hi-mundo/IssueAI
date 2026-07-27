const { spawnSync } = require("node:child_process");
const path = require("node:path");

class IssueAIPromptfooProvider {
  constructor(options = {}) {
    this.options = options;
  }

  id() {
    return "issueai-historical-route";
  }

  async callApi(_prompt, context = {}) {
    const vars = context.vars || {};
    const root = path.resolve(__dirname, "..", "..");
    const outputDir = process.env.ISSUEAI_OUTPUT_DIR || path.join("/tmp", "issueai-promptfoo");
    const command = [
      path.join(root, "evals", "scripts", "run_issueai_case_eval.py"),
      "--case-id",
      String(vars.case_id || ""),
      "--ground-truth",
      process.env.ISSUEAI_GROUND_TRUTH || "",
      "--repos-root",
      process.env.ISSUEAI_REPOS_ROOT || "",
      "--artifacts-root",
      process.env.ISSUEAI_ARTIFACTS_ROOT || "",
      "--graph",
      process.env.ISSUEAI_GRAPH || "",
      "--output-dir",
      outputDir,
    ];
    const result = spawnSync("python3", command, {
      cwd: root,
      encoding: "utf8",
    });
    if (result.status !== 0) {
      throw new Error((result.stderr || result.stdout || "IssueAI promptfoo provider failed").trim());
    }
    return {
      output: (result.stdout || "").trim(),
    };
  }
}

module.exports = IssueAIPromptfooProvider;
