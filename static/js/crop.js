// ===============================
// Selectors
// ===============================
const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");

const presetSelect = document.getElementById("preset");
const marginInput = document.getElementById("crop-margin");
const aspectSelect = document.getElementById("aspect");
const rotateCheckbox = document.getElementById("rotate");
const filterSelect = document.getElementById("filter");
const intensityInput = document.getElementById("intensity");

const previewBtn = document.getElementById("preview-btn");
const processBtn = document.getElementById("process-btn");

const previewBox = document.getElementById("preview-box");
const progressFill = document.getElementById("progress-fill");
const statusText = document.getElementById("status-text");
const progressInfo = document.getElementById("progress-info");
const downloadBtn = document.getElementById("download-btn");

let lastZipUrl = null;

function getErrorMessage(code) {
    switch (code) {
        case 1001:
            return "No face detected.";
        case 1002:
            return "Failed to read image.";
        case 1003:
            return "Cropping failed.";
        case 1004:
            return "Saving failed.";
        default:
            return "Unknown error.";
    }
}

// ===============================
// UI helpers
// ===============================
function updateFileListUI(files) {
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

function setProgress(pct) {
    progressFill.style.width = pct + "%";
}

function setStatus(text) {
    statusText.textContent = text || "";
}

function setProgressInfo(text) {
    progressInfo.textContent = text || "";
}

function hideErrorBanner() {
    if (!errorBanner) return;
    errorBanner.style.display = "none";
    errorBanner.textContent = "";
}

function showErrorBanner(code) {
    if (!errorBanner) return;
    errorBanner.textContent = getErrorMessage(code);
    errorBanner.style.display = "block";
}

function renderBeforeAfter(beforeUrl, afterUrl, errorMsg) {
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
// Clicking upload box = open file selector
// ===============================
dropZone.addEventListener("click", () => fileInput.click());

// ===============================
// Drag & drop logic
// ===============================
dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");

    const dt = e.dataTransfer;
    if (!dt.files || dt.files.length === 0) return;

    // Convert FileList → DataTransfer so we can assign it
    const transfer = new DataTransfer();
    for (let i = 0; i < dt.files.length; i++) {
        transfer.items.add(dt.files[i]);
    }
    fileInput.files = transfer.files;

    updateFileListUI(fileInput.files);
});

// ===============================
// When files selected normally (click dialog)
// ===============================
fileInput.addEventListener("change", () => {
    updateFileListUI(fileInput.files);
});

// ===============================
// Preview Button
// ===============================
previewBtn.addEventListener("click", async () => {
    const files = fileInput.files;
    if (!files || files.length === 0) {
        alert("Please upload at least one image.");
        return;
    }

    const formData = new FormData();
    formData.append("preset_label", presetSelect.value);
    formData.append("margin", marginInput.value);
    formData.append("filter_name", filterSelect.value);
    formData.append("intensity", intensityInput.value);
    formData.append("aspect_ratio", aspectSelect.value);
    formData.append("rotate", rotateCheckbox.checked ? "true" : "false");
    formData.append("file", files[0]);

    setProgress(10);
    setStatus("Generating preview...");
    previewBox.innerHTML = `<p class="placeholder">Processing preview...</p>`;
    downloadBtn.disabled = true;
    hideErrorBanner();

    try {
        const res = await fetch("/api/crop/preview", {
            method: "POST",
            body: formData,
        });

        const data = await res.json();

        if (!res.ok || data.error_code !== 0) {
            const message = data.error || getErrorMessage(data.error_code);
            showErrorBanner(data.error_code);
            setProgress(0);
            setStatus(message || "Preview failed.");
            previewBox.innerHTML = `<p style="color:#f88;">${message}</p>`;
            return;
        }

        hideErrorBanner();
        setProgress(80);
        renderBeforeAfter(data.before_url, data.after_url);
        setStatus(data.message || "Preview generated.");
        setProgress(100);
    } catch (err) {
        setProgress(0);
        setStatus("Network error during preview.");
    }
});

// ===============================
// Process All
// ===============================
processBtn.addEventListener("click", async () => {
    const files = fileInput.files;
    if (!files || files.length === 0) {
        alert("Please upload at least one image.");
        return;
    }

    const formData = new FormData();
    formData.append("preset_label", presetSelect.value);
    formData.append("margin", marginInput.value);
    formData.append("filter_name", filterSelect.value);
    formData.append("intensity", intensityInput.value);
    formData.append("aspect_ratio", aspectSelect.value);
    formData.append("rotate", rotateCheckbox.checked ? "true" : "false");

    for (const f of files) formData.append("files", f);

    setProgress(10);
    setStatus("Processing images...");
    setProgressInfo("");
    downloadBtn.disabled = true;
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
            setProgressInfo((data.processed || 0) + "/" + (data.total || 0));
            return;
        }

        hideErrorBanner();
        setProgress(100);
        setStatus(data.message);
        setProgressInfo(`${data.processed}/${data.total} images processed`);
        lastZipUrl = data.zip_url;
        downloadBtn.disabled = !lastZipUrl;
    } catch (err) {
        setProgress(0);
        setStatus("Network error during processing.");
    }
});

// ===============================
// Download ZIP
// ===============================
downloadBtn.addEventListener("click", () => {
    if (!lastZipUrl) return;
    window.open(lastZipUrl, "_blank");
});
