// ===============================
// Selectors
// ===============================
const dropZone       = document.getElementById("drop-zone");
const fileInput      = document.getElementById("file-input");

const presetSelect   = document.getElementById("preset");
const marginInput    = document.getElementById("crop-margin");
const aspectSelect   = document.getElementById("aspect");
const rotateCheckbox = document.getElementById("rotate");
const filterSelect   = document.getElementById("filter");
const intensityInput = document.getElementById("intensity");

const previewBtn     = document.getElementById("preview-btn");
const processBtn     = document.getElementById("process-btn");

const previewBox     = document.getElementById("preview-box");
const progressFill   = document.getElementById("progress-fill");
const statusText     = document.getElementById("status-text");
const progressInfo   = document.getElementById("progress-info");
const downloadBtn    = document.getElementById("download-btn");
const errorBanner    = document.getElementById("error-banner");

let lastZipUrl = null;


// ===============================
// Backend presets (from template)
// ===============================
const presetsElement = document.getElementById("builtin-presets");
const BUILTIN_PRESETS = (() => {
    if (!presetsElement) return {};
    try {
        return JSON.parse(presetsElement.textContent);
    } catch (err) {
        console.error("Failed to parse builtin presets JSON:", err);
        return {};
    }
})();


// ===============================
// Error helper
// ===============================
function getErrorMessage(code) {
    switch (code) {
        case 1001: return "No face detected.";
        case 1002: return "Failed to read image.";
        case 1003: return "Cropping failed.";
        case 1004: return "Saving failed.";
        default:   return "Unknown error.";
    }
}


// ===============================
// Apply preset → UI
// ===============================
function applyBackendPreset(presetKey) {
    if (!presetKey) return;
    const preset = BUILTIN_PRESETS[presetKey];
    if (!preset) return;

    const params = preset.params || {};

    // Margin: auto/frontal/profile etc. all collapsed into one UI field
    if (marginInput) {
        if (params.frontal_margin !== undefined) {
            marginInput.value = params.frontal_margin;
        } else if (params.margin !== undefined) {
            marginInput.value = params.margin;
        } else {
            // fallback
            marginInput.value = 20;
        }
    }

    // Aspect ratio: use preset.ratio string, else "None"
    if (aspectSelect) {
        if (preset.ratio) {
            aspectSelect.value = preset.ratio;
        } else {
            aspectSelect.value = "None";
        }
    }

    // Rotate: default to preset.rotate, else true
    if (rotateCheckbox) {
        const r = preset.rotate;
        rotateCheckbox.checked = (r === undefined) ? true : !!r;
    }

    // Reset filter + intensity for fresh view
    if (filterSelect)   filterSelect.value = "None";
    if (intensityInput) intensityInput.value = 50;
}

// Hook into preset dropdown
if (presetSelect) {
    presetSelect.addEventListener("change", () => {
        applyBackendPreset(presetSelect.value);
    });

    // Apply once on load for initial default
    if (presetSelect.value) {
        applyBackendPreset(presetSelect.value);
    }
}


// ===============================
// UI helpers (unchanged)
// ===============================
function updateFileListUI(files) {
    if (!dropZone) return;

    if (!files || files.length === 0) {
        dropZone.innerHTML = `
            <label for="file-input">
              Drop File(s) Here<br>or<br>Click to Upload
            </label>
        `;
        return;
    }

    dropZone.innerHTML = `
        <label for="file-input">
          <strong>${files.length}</strong> file(s) loaded<br>
          Click to choose different files
        </label>
    `;
}

const setProgress = pct => {
    if (progressFill) progressFill.style.width = pct + "%";
};

const setStatus = text => {
    if (statusText) statusText.textContent = text || "";
};

const setProgressInfo = text => {
    if (progressInfo) progressInfo.textContent = text || "";
};

function hideErrorBanner() {
    if (errorBanner) {
        errorBanner.style.display = "none";
        errorBanner.textContent = "";
    }
}

function showErrorBanner(code) {
    if (errorBanner) {
        errorBanner.textContent = getErrorMessage(code);
        errorBanner.style.display = "block";
    }
}

function renderBeforeAfter(beforeUrl, afterUrl, errorMsg) {
    if (!previewBox) return;

    if (errorMsg && !afterUrl) {
        previewBox.innerHTML = `<p style="color:#f88; text-align:center;">${errorMsg}</p>`;
        return;
    }

    previewBox.innerHTML = `
        <div class="before-after-wrapper">
            <div class="img-container">
                <img src="${beforeUrl}" alt="Before">
            </div>
            <div class="img-container">
                <img src="${afterUrl}" alt="After">
            </div>
        </div>
    `;
}


// ===============================
// Upload Handling (unchanged)
// ===============================
if (dropZone && fileInput) {
    dropZone.addEventListener("click", () => fileInput.click());

    dropZone.addEventListener("dragover", e => {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("dragover");
    });

    dropZone.addEventListener("drop", e => {
        e.preventDefault();
        dropZone.classList.remove("dragover");

        const dt = e.dataTransfer;
        if (!dt.files || dt.files.length === 0) return;

        const transfer = new DataTransfer();
        for (let i = 0; i < dt.files.length; i++) transfer.items.add(dt.files[i]);
        fileInput.files = transfer.files;

        updateFileListUI(fileInput.files);
    });

    fileInput.addEventListener("change", () => {
        updateFileListUI(fileInput.files);
    });
}


// ===============================
// Preview Button (minor change: still sends preset key)
// ===============================
if (previewBtn) {
    previewBtn.addEventListener("click", async () => {
        const files = fileInput.files;
        if (!files || files.length === 0) {
            alert("Please upload an image first.");
            return;
        }

        hideErrorBanner();
        setProgress(20);
        setStatus("Generating crop variants...");

        const variantsBox = document.getElementById("variants-box");
        variantsBox.innerHTML = `<p class="placeholder">Generating previews...</p>`;

        const formData = new FormData();
        formData.append("file", files[0]);

        const res = await fetch("/preview", { // <-- fixed endpoint
            method: "POST",
            body: formData,
        });

        const data = await res.json();
        variantsBox.innerHTML = "";

        if (!data.ok) {
            variantsBox.innerHTML = `<p style="color:#f55;">${data.message}</p>`;
            setProgress(0);
            setStatus("Preview failed");
            return;
        }

        window.selectedMethod = null;
        setStatus("Select a crop variant");

        Object.entries(data.variants).forEach(([method, url]) => {
            const img = document.createElement("img");
            img.src = url;
            img.className = "preview-thumb";
            img.dataset.method = method;

            img.style.width = "160px";
            img.style.cursor = "pointer";
            img.style.border = "3px solid transparent";
            img.style.borderRadius = "6px";

            img.onclick = () => {
                document.querySelectorAll(".preview-thumb")
                    .forEach(x => x.style.borderColor = "transparent");
                img.style.borderColor = "#4CAF50";
                window.selectedMethod = method;
                setStatus(`Selected: ${method}`);
            };

            variantsBox.appendChild(img);
        });

        setProgress(100);
    });
}

// ===============================
// Process All (unchanged API contract)
// ===============================
if (processBtn) {
    processBtn.addEventListener("click", async () => {
        const files = fileInput.files;
        if (!files || files.length === 0) {
            alert("Please upload at least one image.");
            return;
        }

        const formData = new FormData();
        formData.append("preset_label", window.selectedMethod || presetSelect?.value || "");
        formData.append("margin",       marginInput?.value || 30);
        formData.append("filter_name",  filterSelect?.value || "None");
        formData.append("intensity",    intensityInput?.value || 50);
        formData.append("aspect_ratio", aspectSelect?.value || "None");
        formData.append("rotate",       rotateCheckbox?.checked ? "true" : "false");

        for (const file of files) formData.append("files", file);

        setProgress(10);
        setStatus("Processing images...");
        setProgressInfo("");
        if (downloadBtn) downloadBtn.disabled = true;
        hideErrorBanner();

        try {
            const res = await fetch("/api/crop/process", {
                method: "POST",
                body: formData,
            });

            const data = await res.json();

            if (!res.ok || data.error_code !== 0) {
                const message = data.error || getErrorMessage(data.error_code);
                showErrorBanner(data.error_code);
                setProgress(0);
                setStatus(message || "Processing failed.");
                setProgressInfo(`${data.processed || 0}/${data.total || 0}`);
                return;
            }

            hideErrorBanner();
            setProgress(100);
            setStatus(data.message);
            setProgressInfo(`${data.processed}/${data.total} images processed`);
            lastZipUrl = data.zip_url;
            if (downloadBtn) downloadBtn.disabled = !lastZipUrl;
        } catch {
            setProgress(0);
            setStatus("Network error during processing.");
        }
    });
}


// ===============================
// Download ZIP
// ===============================
if (downloadBtn) {
    downloadBtn.addEventListener("click", () => {
        if (!lastZipUrl) return;
        window.open(lastZipUrl, "_blank");
    });
}


// ===============================
// User presets in localStorage (unchanged)
// ===============================
function loadUserPresets() {
    const raw = localStorage.getItem("cropanywhere_user_presets");
    if (!raw) return {};
    try {
        return JSON.parse(raw);
    } catch {
        return {};
    }
}

function saveUserPresets(presets) {
    localStorage.setItem("cropanywhere_user_presets", JSON.stringify(presets));
}

function refreshUserPresetDropdown() {
    const presets = loadUserPresets();
    const dropdown = document.getElementById("saved-presets");
    if (!dropdown) return;

    dropdown.innerHTML = `<option value="">Select a saved preset</option>`;

    for (const name of Object.keys(presets)) {
        const opt = document.createElement("option");
        opt.value = name;
        opt.textContent = name;
        dropdown.appendChild(opt);
    }
}

refreshUserPresetDropdown();

const savePresetBtn = document.getElementById("save-preset-btn");

if (savePresetBtn) {
    savePresetBtn.addEventListener("click", () => {
        const nameField = document.getElementById("preset-name");
        const name = nameField.value.trim();
        if (!name) {
            alert("Preset name cannot be empty.");
            return;
        }

        const presets = loadUserPresets();

        presets[name] = {
            margin:    marginInput.value,
            aspect:    aspectSelect.value,
            rotate:    rotateCheckbox.checked,
            filter:    filterSelect.value,
            intensity: intensityInput.value,
        };

        saveUserPresets(presets);
        refreshUserPresetDropdown();
        alert(`Preset "${name}" saved!`);
    });
}

const loadPresetDropdown = document.getElementById("saved-presets");

if (loadPresetDropdown) {
    loadPresetDropdown.addEventListener("change", () => {
        const name = loadPresetDropdown.value;
        if (!name) return;

        const presets = loadUserPresets();
        const p = presets[name];
        if (!p) return;

        if (marginInput)    marginInput.value = p.margin;
        if (aspectSelect)   aspectSelect.value = p.aspect;
        if (rotateCheckbox) rotateCheckbox.checked = p.rotate;
        if (filterSelect)   filterSelect.value = p.filter;
        if (intensityInput) intensityInput.value = p.intensity;
    });
}
