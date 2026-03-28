import js from "@eslint/js";
import tsParser from "@typescript-eslint/parser";
import tsPlugin from "@typescript-eslint/eslint-plugin";
import vuePlugin from "eslint-plugin-vue";
import prettier from "eslint-config-prettier";

export default [
  {
    ignores: ["dist", "coverage"],
  },
  js.configs.recommended,
  ...vuePlugin.configs["flat/recommended"],
  {
    files: ["**/*.{ts,tsx,vue}"],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: "latest",
        sourceType: "module",
      },
    },
    plugins: {
      "@typescript-eslint": tsPlugin,
    },
    rules: {
      "@typescript-eslint/no-unused-vars": ["error", { "argsIgnorePattern": "^_" }],
      "max-len": [
        "error",
        {
          "code": 140,
          "ignoreUrls": true,
          "ignoreStrings": true,
          "ignoreTemplateLiterals": true
        }
      ],
    },
  },
  prettier,
];
