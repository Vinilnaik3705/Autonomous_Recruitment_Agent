import js from "@eslint/js";
import globals from "globals";
import react from "eslint-plugin-react";
export default [
  {
    files: ["src/workspace/**/*.{jsx,mjs}", "vite.config.mjs"],
    ...js.configs.recommended,
    languageOptions: {
      globals: { ...globals.browser, ...globals.node },
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    plugins: { react },
    rules: {
      ...js.configs.recommended.rules,
      "react/jsx-uses-vars": "error",
      "react/jsx-uses-react": "error",
    },
  },
];
