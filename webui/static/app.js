(() => {
  "use strict";

  const form = document.getElementById("assessment-form");
  if (!form) return;

  const panels = Array.from(document.querySelectorAll(".source-panel"));
  const modeInputs = Array.from(
    document.querySelectorAll('input[name="input_kind"]')
  );
  const sourceFields = {
    c: document.getElementById("c_source"),
    sv_core: document.getElementById("sv_core_source"),
    sv_tb: document.getElementById("sv_tb_source"),
  };
  const sourceMetadata = {
    c: { title: "C / C++ generator", language: "cpp", uri: "generator.cpp" },
    sv_core: { title: "SystemVerilog core", language: "systemverilog", uri: "rng_core.sv" },
    sv_tb: { title: "SystemVerilog testbench", language: "systemverilog", uri: "tb.sv" },
  };

  const editorHost = document.getElementById("source-editor");
  const editorTitle = document.getElementById("editor-title");
  const editorLanguage = document.getElementById("editor-language");
  const editorLoading = document.getElementById("editor-loading");
  const editorEmpty = document.getElementById("editor-empty");
  const svTabs = document.getElementById("sv-editor-tabs");
  const tabButtons = Array.from(document.querySelectorAll("[data-editor-key]"));

  let editor = null;
  let monacoApi = null;
  let currentMode = document.querySelector(
    'input[name="input_kind"]:checked'
  )?.value || "files";
  let activeSVKey = "sv_core";
  const models = new Map();

  function selectedSourceKey() {
    if (currentMode === "c") return "c";
    if (currentMode === "systemverilog") return activeSVKey;
    return null;
  }

  function cLanguage() {
    return document.getElementById("c_language")?.value === "c" ? "c" : "cpp";
  }

  function updateEditorChrome(key) {
    if (!key) {
      editorTitle.textContent = "Bitstream files";
      editorLanguage.textContent = "No editor";
      svTabs.hidden = true;
      editorHost.hidden = true;
      editorLoading.hidden = true;
      editorEmpty.hidden = false;
      return;
    }

    const metadata = sourceMetadata[key];
    editorTitle.textContent = metadata.title;
    editorLanguage.textContent = key === "c" ? cLanguage().toUpperCase() : "SystemVerilog";
    svTabs.hidden = currentMode !== "systemverilog";
    editorEmpty.hidden = true;

    tabButtons.forEach((button) => {
      const active = button.dataset.editorKey === key;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", String(active));
    });

    if (!editor || !models.has(key)) {
      editorHost.hidden = true;
      editorLoading.hidden = false;
      return;
    }

    editorLoading.hidden = true;
    editorHost.hidden = false;
    editor.setModel(models.get(key));
    editor.focus();
    editor.layout();
  }

  function selectMode(mode) {
    currentMode = mode;
    panels.forEach((panel) => {
      const active = panel.dataset.mode === mode;
      panel.hidden = !active;
      panel.querySelectorAll("input, select").forEach((field) => {
        field.disabled = !active;
      });
    });

    sourceFields.c.disabled = mode !== "c";
    sourceFields.sv_core.disabled = mode !== "systemverilog";
    sourceFields.sv_tb.disabled = mode !== "systemverilog";
    updateEditorChrome(selectedSourceKey());
  }

  function setSourceValue(key, value) {
    const field = sourceFields[key];
    if (field) field.value = value;
    const model = models.get(key);
    if (model && model.getValue() !== value) model.setValue(value);
  }

  function loadSource(fileInputId, sourceKey) {
    const fileInput = document.getElementById(fileInputId);
    fileInput?.addEventListener("change", async () => {
      if (fileInput.files.length !== 1) return;
      setSourceValue(sourceKey, await fileInput.files[0].text());
      if (sourceKey.startsWith("sv_")) {
        activeSVKey = sourceKey;
        updateEditorChrome(sourceKey);
      }
    });
  }

  function registerSystemVerilog(monaco) {
    if (monaco.languages.getLanguages().some((language) => language.id === "systemverilog")) {
      return;
    }

    const keywords = [
      "always", "always_comb", "always_ff", "always_latch", "assign", "automatic",
      "begin", "bit", "break", "case", "casex", "casez", "class", "clocking",
      "const", "continue", "default", "disable", "do", "else", "end", "endcase",
      "endclass", "endfunction", "endgenerate", "endmodule", "endpackage",
      "endtask", "enum", "for", "force", "foreach", "forever", "fork", "function",
      "generate", "genvar", "if", "initial", "inout", "input", "integer",
      "interface", "localparam", "logic", "longint", "module", "output", "package",
      "parameter", "rand", "reg", "repeat", "return", "signed", "static", "string",
      "struct", "task", "time", "typedef", "union", "unsigned", "virtual", "void",
      "wait", "while", "wire"
    ];

    monaco.languages.register({ id: "systemverilog" });
    monaco.languages.setLanguageConfiguration("systemverilog", {
      comments: { lineComment: "//", blockComment: ["/*", "*/"] },
      brackets: [["{", "}"], ["[", "]"], ["(", ")"]],
      autoClosingPairs: [
        { open: "{", close: "}" },
        { open: "[", close: "]" },
        { open: "(", close: ")" },
        { open: '"', close: '"' }
      ]
    });
    monaco.languages.setMonarchTokensProvider("systemverilog", {
      defaultToken: "",
      keywords,
      tokenizer: {
        root: [
          [/\/[/*]/, { cases: { "\/\/": "comment", "\/\*": { token: "comment", next: "@comment" } } }],
          [/\d+'[sS]?[bBoOdDhH][0-9a-fA-F_xXzZ?]+/, "number"],
          [/\b\d+(?:\.\d+)?\b/, "number"],
          [/[a-zA-Z_$][\w$]*/, { cases: { "@keywords": "keyword", "@default": "identifier" } }],
          [/"([^"\\]|\\.)*$/, "string.invalid"],
          [/"/, { token: "string.quote", bracket: "@open", next: "@string" }],
          [/[{}()[\]]/, "@brackets"],
          [/[;,.]/, "delimiter"],
          [/[=><!~?:&|+\-*\/^%]+/, "operator"]
        ],
        comment: [
          [/[^/*]+/, "comment"],
          [/\*\//, { token: "comment", next: "@pop" }],
          [/[/*]/, "comment"]
        ],
        string: [
          [/[^\\"]+/, "string"],
          [/\\./, "string.escape"],
          [/"/, { token: "string.quote", bracket: "@close", next: "@pop" }]
        ]
      }
    });
  }

  function initializeMonaco(monaco) {
    monacoApi = monaco;
    registerSystemVerilog(monaco);

    Object.entries(sourceMetadata).forEach(([key, metadata]) => {
      const language = key === "c" ? cLanguage() : metadata.language;
      const model = monaco.editor.createModel(
        sourceFields[key].value,
        language,
        monaco.Uri.parse(`inmemory://spur/${metadata.uri}`)
      );
      models.set(key, model);
      model.onDidChangeContent(() => {
        sourceFields[key].value = model.getValue();
      });
    });

    editor = monaco.editor.create(editorHost, {
      model: models.get("c"),
      theme: "vs-dark",
      minimap: { enabled: true },
      automaticLayout: true,
      fontSize: 13,
      lineHeight: 20,
      scrollBeyondLastLine: false,
      tabSize: 2,
      insertSpaces: true,
      wordWrap: "off",
      renderWhitespace: "selection",
      smoothScrolling: true
    });
    updateEditorChrome(selectedSourceKey());
  }

  const inputFiles = document.getElementById("input_files");
  const fileCount = document.getElementById("file-count");
  inputFiles?.addEventListener("change", () => {
    const count = inputFiles.files.length;
    fileCount.textContent = count === 0
      ? "No files selected."
      : count === 1
        ? "1 file selected: a single dashboard will be generated."
        : `${count} files selected: ${count} assessments will be compared.`;
  });

  loadSource("c_file", "c");
  loadSource("sv_core_file", "sv_core");
  loadSource("sv_tb_file", "sv_tb");

  const dataEl = document.getElementById("library-examples-data");
  let libraryExamples = [];
  try {
    libraryExamples = JSON.parse(dataEl?.textContent || "[]");
  } catch (_error) {
    libraryExamples = [];
  }
  const examplesById = new Map(libraryExamples.map((example) => [example.id, example]));
  const librarySelect = document.getElementById("c_library");
  const languageSelect = document.getElementById("c_language");

  librarySelect?.addEventListener("change", () => {
    const example = examplesById.get(librarySelect.value);
    if (!example) return;
    setSourceValue("c", example.source);
    languageSelect.value = "cpp";
    if (monacoApi && models.has("c")) {
      monacoApi.editor.setModelLanguage(models.get("c"), "cpp");
    }
    document.getElementById("c_generator_name").value = example.generator_name;
    document.getElementById("c_output_format").value = example.output_format;
    updateEditorChrome("c");
  });

  languageSelect?.addEventListener("change", () => {
    if (monacoApi && models.has("c")) {
      monacoApi.editor.setModelLanguage(models.get("c"), cLanguage());
    }
    if (currentMode === "c") updateEditorChrome("c");
  });

  modeInputs.forEach((input) => {
    input.addEventListener("change", () => {
      if (input.checked) selectMode(input.value);
    });
  });

  tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      activeSVKey = button.dataset.editorKey;
      updateEditorChrome(activeSVKey);
    });
  });

  // Monaco models are not form controls. Synchronize every model immediately
  // before the browser serializes this form for the existing POST endpoint.
  form.addEventListener("submit", () => {
    models.forEach((model, key) => {
      sourceFields[key].value = model.getValue();
    });
  });

  selectMode(currentMode);

  const loaderScript = document.querySelector("script[data-monaco-base]");
  const monacoBase = loaderScript?.dataset.monacoBase;
  if (!monacoBase || typeof window.require !== "function") {
    editorLoading.textContent = "Monaco Editor could not be loaded.";
    return;
  }

  window.MonacoEnvironment = {
    getWorkerUrl() {
      const workerUrl = `${window.location.origin}${monacoBase}/base/worker/workerMain.js`;
      const source = `self.MonacoEnvironment={baseUrl:'${window.location.origin}${monacoBase}/'};importScripts('${workerUrl}');`;
      return `data:text/javascript;charset=utf-8,${encodeURIComponent(source)}`;
    }
  };
  window.require.config({ paths: { vs: monacoBase } });
  window.require(
    ["vs/editor/editor.main"],
    () => initializeMonaco(window.monaco),
    () => {
      editorLoading.textContent = "Monaco Editor failed to initialize.";
    }
  );
})();
