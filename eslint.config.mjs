import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    ".venv/**",
    "node_modules/**",
    "ml/**",
    "tests/e2e/test-results/**",
    "playwright-report/**",
  ]),
  {
    rules: {
      // OCR/analysis payloads are schemaless JSON from the backend; typed narrowing is future work.
      "@typescript-eslint/no-explicit-any": "warn",
      // Mount-time data loading (async fetch -> setState) is the intended pattern here.
      "react-hooks/set-state-in-effect": "off",
    },
  },
]);

export default eslintConfig;
