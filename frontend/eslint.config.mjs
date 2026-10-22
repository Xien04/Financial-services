import { defineConfig, globalIgnores } from "eslint/config";
import js from "@eslint/js";
import tseslint from "typescript-eslint";

export default defineConfig([
  globalIgnores([".next/**", "out/**", "next-env.d.ts"]),
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.mjs", "next.config.ts"],
    languageOptions: { globals: { process: "readonly", fetch: "readonly", URL: "readonly" } },
  },
]);
