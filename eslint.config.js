import js from '@eslint/js';
import importPlugin from 'eslint-plugin-import';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['**/dist/**', '**/out/**', '**/release/**', '**/node_modules/**'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['apps/web/src/**/*.{ts,tsx}'],
    plugins: {
      import: importPlugin,
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
    },
  },
  {
    files: ['apps/desktop/src/**/*.ts', 'packages/**/*.ts'],
    plugins: { import: importPlugin },
  },
);
