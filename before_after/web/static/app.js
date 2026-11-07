const slots = [null, null];
const fileInputs = document.querySelectorAll('input[type="file"][data-slot]');
const previews = document.querySelectorAll("[data-preview]");
const names = document.querySelectorAll("[data-name]");
const swapBtn = document.getElementById("swap-btn");
const autoDetect = document.getElementById("auto-detect");
const buildBtn = document.getElementById("build-btn");
const statusEl = document.getElementById("status");
const downloadWrap = document.getElementById("download-wrap");

const IMAGE_EXT = /\.(jpe?g|png|webp|gif|bmp|tiff?|heic|heif)$/i;

function isImageFile(file) {
  if (file.type && file.type.startsWith("image/")) return true;
  return IMAGE_EXT.test(file.name || "");
}

function updateBuildButton() {
  buildBtn.disabled = !(slots[0] && slots[1]);
}

function setSlot(index, file) {
  if (!file || !isImageFile(file)) {
    statusEl.textContent = "Please choose a JPG, PNG, HEIC, or WEBP file.";
    return;
  }
  slots[index] = file;
  names[index].textContent = file.name;

  const preview = previews[index];
  preview.innerHTML = "";
  const img = document.createElement("img");
  img.alt = file.name;
  img.src = URL.createObjectURL(file);
  preview.appendChild(img);

  updateBuildButton();
  statusEl.textContent = slots[0] && slots[1] ? "Ready — click Create JPG." : `Photo ${index + 1} added.`;
}

function bindSlot(index) {
  const input = fileInputs[index];
  const preview = previews[index];

  preview.addEventListener("click", () => input.click());
  input.addEventListener("change", () => {
    const file = input.files?.[0];
    if (file) setSlot(index, file);
    input.value = "";
  });

  preview.addEventListener("dragover", (e) => {
    e.preventDefault();
    preview.classList.add("dragover");
  });
  preview.addEventListener("dragleave", () => preview.classList.remove("dragover"));
  preview.addEventListener("drop", (e) => {
    e.preventDefault();
    preview.classList.remove("dragover");
    const file = e.dataTransfer?.files?.[0];
    if (file) setSlot(index, file);
  });
}

bindSlot(0);
bindSlot(1);

swapBtn.addEventListener("click", () => {
  [slots[0], slots[1]] = [slots[1], slots[0]];
  const n0 = names[0].textContent;
  const n1 = names[1].textContent;
  names[0].textContent = n1;
  names[1].textContent = n0;
  previews[0].innerHTML = "";
  previews[1].innerHTML = "";
  [0, 1].forEach((i) => {
    if (!slots[i]) {
      previews[i].innerHTML = '<span class="slot-hint">Click or drop</span>';
      return;
    }
    const img = document.createElement("img");
    img.alt = slots[i].name;
    img.src = URL.createObjectURL(slots[i]);
    previews[i].appendChild(img);
  });
  statusEl.textContent = "Photos swapped.";
});

function clearDownload() {
  downloadWrap.innerHTML = "";
  downloadWrap.hidden = true;
}

buildBtn.addEventListener("click", async () => {
  if (!slots[0] || !slots[1]) return;

  buildBtn.disabled = true;
  clearDownload();
  statusEl.textContent = "Building JPG…";

  const form = new FormData();
  form.append("photo_one", slots[0], slots[0].name);
  form.append("photo_two", slots[1], slots[1].name);
  form.append("auto_detect", autoDetect.checked ? "true" : "false");
  form.append("canvas_size", "2048");
  form.append("jpeg_quality", "92");

  try {
    const response = await fetch("/api/composite", { method: "POST", body: form });
    if (!response.ok) {
      let msg = "Could not create image.";
      try {
        const body = await response.json();
        if (body.detail) msg = typeof body.detail === "string" ? body.detail : msg;
      } catch (_) {
        /* ignore */
      }
      statusEl.textContent = msg;
      updateBuildButton();
      return;
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "before_after.jpg";
    link.className = "download-link";
    link.textContent = "Download before_after.jpg";
    downloadWrap.appendChild(link);
    downloadWrap.hidden = false;
    link.click();

    statusEl.textContent = "Done! If nothing saved, use the download link below.";
  } catch (err) {
    statusEl.textContent = `Error: ${err}. Is the server running?`;
  } finally {
    updateBuildButton();
  }
});

statusEl.textContent = "Add two photos to start.";
