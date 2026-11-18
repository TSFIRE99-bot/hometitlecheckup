// HomeKeep Pro: read the text in a scan or photo, inside the staff member's browser.
// Uses our own copies of Tesseract.js (OCR) and pdf.js (to turn PDF pages into images), both free and open source,
// served from /ocr. The document is fetched from HomeKeep and never sent anywhere else. Nothing is saved until the
// staff member presses Save, and the server treats the text like any other untrusted upload.
import * as pdfjs from "/ocr/pdf.min.mjs";

pdfjs.GlobalWorkerOptions.workerSrc = "/ocr/pdf.worker.min.mjs";

const box = document.getElementById("ocr");
const start = document.getElementById("ocr-start");
const step = document.getElementById("ocr-step");
const detail = document.getElementById("ocr-detail");
const bar = document.getElementById("ocr-bar");
const form = document.getElementById("ocr-form");
const pagesBox = document.getElementById("ocr-pages");
const status = box.querySelector(".ocr-status");
const maxPages = Number(box.dataset.maxPages) || 60;

function say(title, text, fraction) {
  step.textContent = title;
  detail.textContent = text;
  if (fraction !== undefined) bar.style.width = `${Math.round(Math.min(1, Math.max(0, fraction)) * 100)}%`;
}

function fail(text) {
  status.classList.add("error");
  say("Couldn't read this file", text, 0);
  start.classList.remove("is-busy");
  start.textContent = "Try again";
  start.disabled = false;
}

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = src;
    s.onload = resolve;
    s.onerror = () => reject(new Error(`Couldn't load ${src}`));
    document.head.appendChild(s);
  });
}

async function pagesToRead(blob) {
  if (box.dataset.pdf !== "yes") return [blob];
  const pdf = await pdfjs.getDocument({ data: new Uint8Array(await blob.arrayBuffer()) }).promise;
  if (pdf.numPages > maxPages) throw new Error(`This PDF has ${pdf.numPages} pages; the limit is ${maxPages}.`);
  const images = [];
  for (let n = 1; n <= pdf.numPages; n++) {
    say("Preparing pages", `Page ${n} of ${pdf.numPages}`, (n - 1) / pdf.numPages * 0.1);
    const page = await pdf.getPage(n);
    const viewport = page.getViewport({ scale: 2 });          // about 150 dpi for a letter page: enough for OCR
    const canvas = document.createElement("canvas");
    canvas.width = viewport.width;
    canvas.height = viewport.height;
    await page.render({ canvasContext: canvas.getContext("2d"), viewport }).promise;
    images.push(canvas);
  }
  return images;
}

function showText(texts) {
  pagesBox.textContent = "";
  texts.forEach((text, i) => {
    const label = document.createElement("label");
    label.className = "field-label";
    label.textContent = texts.length > 1 ? `Page ${i + 1}` : "Text";
    const area = document.createElement("textarea");
    area.name = "page";
    area.rows = Math.min(18, Math.max(6, text.split("\n").length + 1));
    area.value = text;
    area.className = "ocr-text";
    label.appendChild(area);
    pagesBox.appendChild(label);
  });
  form.hidden = false;
}

start.addEventListener("click", async () => {
  if (start.classList.contains("is-busy")) return;
  status.classList.remove("error");
  start.classList.add("is-busy");
  start.textContent = start.dataset.busyLabel || "Reading…";
  start.disabled = false;
  let worker;
  try {
    say("Opening the file", "Downloading it from HomeKeep (not from anywhere else).", 0.02);
    const res = await fetch(box.dataset.file, { credentials: "same-origin" });
    const type = res.headers.get("content-type") || "";
    if (!res.ok || type.includes("text/html")) throw new Error("HomeKeep wouldn't send the file. Is it released?");
    const items = await pagesToRead(await res.blob());

    say("Starting the reader", "The first time takes a little longer: the reader downloads from HomeKeep (about 10 MB).", 0.1);
    if (!window.Tesseract) await loadScript("/ocr/tesseract.min.js");
    let current = 0;
    worker = await window.Tesseract.createWorker("eng", 1, {
      workerPath: "/ocr/worker.min.js",
      corePath: "/ocr/",
      langPath: "/ocr/lang",
      workerBlobURL: false,
      logger: (m) => {
        if (m.status === "recognizing text") {
          say("Reading", `Page ${current + 1} of ${items.length}`, 0.12 + 0.88 * (current + m.progress) / items.length);
        }
      },
    });
    const texts = [];
    for (current = 0; current < items.length; current++) {
      const { data } = await worker.recognize(items[current]);
      texts.push((data.text || "").trim());
    }
    const words = texts.join(" ").split(/\s+/).filter(Boolean).length;
    if (words < 4) throw new Error("No readable words were found. It may be too blurry or handwritten; type the facts in on the review page.");
    say("Done", `${words} words read from ${texts.length} page${texts.length === 1 ? "" : "s"}. Check it below, then save.`, 1);
    start.classList.remove("is-busy");
    start.textContent = "Read again";
    showText(texts);
  } catch (err) {
    fail(err && err.message ? err.message : "Something went wrong while reading.");
  } finally {
    if (worker) await worker.terminate();
  }
});
