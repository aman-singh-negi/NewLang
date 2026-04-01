/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Frost (Nord-inspired) dark theme + syntax highlighting for the `language` Monaco mode.
 */
export function setupMonaco(monaco: any): void {
  monaco.editor.defineTheme("frost-language", {
    base: "vs-dark",
    inherit: true,
    rules: [
      { token: "keyword.language", foreground: "88c0d0", fontStyle: "bold" },
      { token: "number.language", foreground: "b48ead" },
      { token: "identifier.language", foreground: "8fbcbb" },
      { token: "operator.language", foreground: "d8dee9" },
      { token: "delimiter.bracket.language", foreground: "ebcb8b" },
      { token: "string.language", foreground: "a3be8c" },
      { token: "comment.language", foreground: "616e88", fontStyle: "italic" },
    ],
    colors: {
      "editor.background": "#1e2229",
      "editor.lineHighlightBackground": "#2e3440",
      "editorLineNumber.foreground": "#4c566a",
      "editorLineNumber.activeForeground": "#d8dee9",
      "editorCursor.foreground": "#88c0d0",
      "editor.selectionBackground": "#5e81ac55",
      "editor.inactiveSelectionBackground": "#434c5e66",
      "minimap.background": "#1e2229",
      "editorWhitespace.foreground": "#3b4252",
      "editorBracketHighlight.foreground1": "#88c0d0",
      "editorBracketHighlight.foreground2": "#a3be8c",
      "editorBracketHighlight.foreground3": "#81a1c1",
    },
  });

  monaco.languages.register({ id: "language" });

  monaco.languages.setMonarchTokensProvider("language", {
    defaultToken: "",
    tokenizer: {
      root: [
        [/\b(var|when|otherwise|loop|func|show|return)\b/, "keyword.language"],
        [/"(?:[^"\\]|\\.)*"/, "string.language"],
        [/\d+\.?\d*/, "number.language"],
        [/[+\-*/=<>!]+|==|!=|<=|>=/, "operator.language"],
        [/[{}()\[\];,]/, "delimiter.bracket.language"],
        [/[a-zA-Z_]\w*/, "identifier.language"],
      ],
    },
  });
}
