import { useEffect, useRef, useState } from "react";

/** Renders a PDF's pages to canvases with PDF.js, so the preview works on every device
 *  (Android Chrome and many in-app browsers cannot show a PDF inside the page). Loaded on demand. */
export default function PdfPages({ src }: { src: string }) {
  const box = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const pdfjs = await import("pdfjs-dist");
        // Served as .js from /public: some servers (our nginx) send .mjs as octet-stream, and browsers then
        // refuse the module worker. Versioned name, so a cached bad copy can never be reused.
        pdfjs.GlobalWorkerOptions.workerSrc = "/pdfjs/pdf.worker-4.4.168.min.js";
        const data = await (await fetch(src, { credentials: "include" })).arrayBuffer();
        const doc = await pdfjs.getDocument({ data }).promise;
        const host = box.current;
        if (!host || cancelled) return;
        host.innerHTML = "";
        const width = Math.max(240, Math.min((host.parentElement?.clientWidth || 820) - 36, 820));  // host is display: contents
        for (let n = 1; n <= doc.numPages; n++) {
          const page = await doc.getPage(n);
          const scale = (width / page.getViewport({ scale: 1 }).width) * (window.devicePixelRatio || 1);
          const vp = page.getViewport({ scale });
          const canvas = document.createElement("canvas");
          canvas.width = vp.width;
          canvas.height = vp.height;
          host.appendChild(canvas);
          await page.render({ canvasContext: canvas.getContext("2d")!, viewport: vp }).promise;
          if (cancelled) return;
        }
        setState("ready");
      } catch {
        if (!cancelled) setState("error");
      }
    })();
    return () => { cancelled = true; };
  }, [src]);

  return (
    <div className="pdf-pages">
      {state === "loading" && <div className="pdf-wait"><span className="spinner" />Opening your CV</div>}
      {state === "error" && <div className="pdf-wait">Could not show the preview. Use Download instead.</div>}
      <div ref={box} style={{ display: "contents" }} />
    </div>
  );
}
