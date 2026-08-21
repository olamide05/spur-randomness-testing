(() => {
  "use strict";

  const editors = new Map();
  const form = document.getElementById("assessment-form");
  const panels = Array.from(document.querySelectorAll(".source-panel"));
  const modeInputs = Array.from(
    document.querySelectorAll('input[name="input_kind"]')
  );

  function createEditor(hostId, textareaId, mode) {
    const host = document.getElementById(hostId);
    const textarea = document.getElementById(textareaId);
    if (!host || !textarea || !window.ace) return;

    const aceScript = document.querySelector("script[data-ace-base]");
    if (aceScript?.dataset.aceBase) {
      window.ace.config.set("basePath", aceScript.dataset.aceBase);
    }

    host.hidden = false;
    textarea.classList.add("editor-active");
    const editor = window.ace.edit(host);
    editor.setTheme("ace/theme/tomorrow_night_eighties");
    editor.session.setMode(`ace/mode/${mode}`);
    editor.session.setUseWorker(false);
    editor.session.setUseWrapMode(true);
    editor.session.setTabSize(2);
    editor.session.setUseSoftTabs(true);
    editor.setValue(textarea.value, -1);
    editor.setOptions({
      fontSize: "13px",
      highlightActiveLine: true,
      highlightSelectedWord: true,
      showPrintMargin: false,
    });
    editor.session.on("change", () => {
      textarea.value = editor.getValue();
    });
    editors.set(textareaId, editor);
  }

  function setEditorValue(textareaId, value) {
    const textarea = document.getElementById(textareaId);
    if (!textarea) return;
    textarea.value = value;
    const editor = editors.get(textareaId);
    if (editor) editor.setValue(value, -1);
  }

  function loadSource(fileInputId, textareaId) {
    const fileInput = document.getElementById(fileInputId);
    if (!fileInput) return;
    fileInput.addEventListener("change", async () => {
      if (fileInput.files.length !== 1) return;
      setEditorValue(textareaId, await fileInput.files[0].text());
    });
  }

  function selectMode(mode) {
    panels.forEach((panel) => {
      const active = panel.dataset.mode === mode;
      panel.hidden = !active;
      panel.querySelectorAll("input, textarea, select").forEach((field) => {
        field.disabled = !active;
      });
    });
    window.requestAnimationFrame(() => {
      editors.forEach((editor) => editor.resize());
    });
  }

  const inputFiles = document.getElementById("input_files");
  const fileCount = document.getElementById("file-count");
  inputFiles?.addEventListener("change", () => {
    const count = inputFiles.files.length;
    fileCount.textContent = count === 1
      ? "1 file selected: a single dashboard will be generated."
      : `${count} files selected: the batch report will compare ${count} results.`;
  });

  createEditor("c-editor", "c_source", "c_cpp");
  createEditor("sv-core-editor", "sv_core_source", "verilog");
  createEditor("sv-tb-editor", "sv_tb_source", "verilog");

  loadSource("c_file", "c_source");
  loadSource("sv_core_file", "sv_core_source");
  loadSource("sv_tb_file", "sv_tb_source");

  function loadLibraryExamples() {
    const dataEl = document.getElementById("library-examples-data");
    if (!dataEl) return;
    let examples = [];
    try {
      examples = JSON.parse(dataEl.textContent || "[]");
    } catch (err) {
      return;
    }
    const byId = new Map(examples.map((ex) => [ex.id, ex]));

    const librarySelect = document.getElementById("c_library");
    const languageSelect = document.getElementById("c_language");
    const generatorName = document.getElementById("c_generator_name");
    const outputFormat = document.getElementById("c_output_format");

    librarySelect?.addEventListener("change", () => {
      const example = byId.get(librarySelect.value);
      if (!example) return;
      setEditorValue("c_source", example.source);
      if (languageSelect) languageSelect.value = "cpp";
      if (generatorName) generatorName.value = example.generator_name;
      if (outputFormat) outputFormat.value = example.output_format;
    });
  }
  loadLibraryExamples();

  modeInputs.forEach((input) => {
    input.addEventListener("change", () => selectMode(input.value));
  });
  const selectedMode = document.querySelector(
    'input[name="input_kind"]:checked'
  );
  if (selectedMode) selectMode(selectedMode.value);

  form?.addEventListener("submit", () => {
    editors.forEach((editor, textareaId) => {
      document.getElementById(textareaId).value = editor.getValue();
    });
  });
})();
