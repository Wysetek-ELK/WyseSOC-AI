/**
 * Robust cross-browser clipboard utility.
 *
 * In non-secure contexts (e.g. accessing http://<server-ip>:3000 rather than https:// or localhost),
 * `navigator.clipboard` is strictly undefined in modern browsers for security reasons.
 *
 * This utility uses a multi-tiered approach:
 * 1. Modern Async Clipboard API (when available in Secure Contexts or localhost)
 * 2. Synchronous DOM Range / Selection on pre-formatted span (works across HTTP & inside modals)
 * 3. Unrestricted offscreen textarea fallback (without readonly or opacity:0 flags that block selection)
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  if (text === undefined || text === null) {
    return false;
  }

  // Tier 1: Modern Async Clipboard API (available in Secure Contexts: HTTPS or localhost)
  if (
    typeof window !== "undefined" &&
    typeof navigator !== "undefined" &&
    navigator.clipboard &&
    typeof navigator.clipboard.writeText === "function"
  ) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (err) {
      console.warn("navigator.clipboard.writeText failed, falling back to synchronous DOM methods:", err);
    }
  }

  // Tier 2: Synchronous DOM Range / Selection on pre-formatted span
  // This bypasses input/textarea focus traps, mobile keyboard popups, and readonly restrictions.
  if (typeof document !== "undefined") {
    try {
      const span = document.createElement("span");
      span.textContent = text;
      span.style.all = "unset";
      span.style.position = "fixed";
      span.style.top = "0";
      span.style.left = "-99999px";
      span.style.whiteSpace = "pre";
      span.style.webkitUserSelect = "text";
      span.style.userSelect = "text";
      span.style.zIndex = "999999";
      span.setAttribute("aria-hidden", "true");

      document.body.appendChild(span);

      const range = document.createRange();
      range.selectNodeContents(span);

      const selection = window.getSelection();
      if (selection) {
        selection.removeAllRanges();
        selection.addRange(range);
      }

      let copied = false;
      try {
        copied = document.execCommand("copy");
      } catch {
        copied = false;
      }

      if (selection) {
        selection.removeAllRanges();
      }
      document.body.removeChild(span);

      if (copied) {
        return true;
      }
    } catch (err) {
      console.warn("DOM Range copy failed, trying unrestricted textarea fallback:", err);
    }

    // Tier 3: Unrestricted off-screen Textarea fallback
    // CRITICAL: Do NOT set readonly or opacity:0 as they block selection in Chromium & Safari!
    try {
      const textArea = document.createElement("textarea");
      textArea.value = text;
      textArea.style.position = "fixed";
      textArea.style.top = "0";
      textArea.style.left = "-99999px";
      textArea.style.width = "2em";
      textArea.style.height = "2em";
      textArea.style.padding = "0";
      textArea.style.border = "none";
      textArea.style.outline = "none";
      textArea.style.boxShadow = "none";
      textArea.style.background = "transparent";
      textArea.style.zIndex = "999999";
      textArea.setAttribute("aria-hidden", "true");

      document.body.appendChild(textArea);
      textArea.focus({ preventScroll: true });
      textArea.select();
      textArea.setSelectionRange(0, text.length);

      let copied = false;
      try {
        copied = document.execCommand("copy");
      } catch {
        copied = false;
      }
      document.body.removeChild(textArea);

      if (copied) {
        return true;
      }
    } catch (err) {
      console.error("Textarea fallback failed:", err);
    }
  }

  return false;
}
