import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";
import { defineConfig, globalIgnores } from "eslint/config";

export default defineConfig([
  globalIgnores(["dist", "node_modules", "logs"]),
  {
    files: ["**/*.{ts,tsx}"],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
    },
    rules: {
      "max-len": [
        "warn",
        {
          code: 120,
          tabWidth: 2,
          ignoreUrls: true,
          ignoreStrings: true,
          ignoreTemplateLiterals: true,
          ignoreRegExpLiterals: true,
        },
      ],
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            "@/modules/*/ui/**",
            "@/modules/*/nodes/**",
            "@/modules/*/edges/**",
            "@/modules/*/model/**",
            "@/modules/*/lib/**",
            "@/modules/*/config/**",
            "@/entities/*/api/**",
            "@/entities/*/model/**",
            "@/entities/*/ui/**",
            "@/features/*/ui/**",
            "@/features/*/model/**",
          ],
        },
      ],
    },
  },
]);
