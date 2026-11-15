/**
 * Robust cross-browser clipboard utility.
 *
 * In non-secure contexts (e.g. accessing http://<server-ip>:3000 rather than https:// or localhost),
 * `navigator.clipboard` is strictly undefined in modern browsers for security reasons.
 *
 * This utility tries `navigator.clipboard.writeText` first when available and authorized,
 * and seamlessly falls back to a hidden textarea with `document.execCommand('copy')`.
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  if (text === undefined || text === null) {
    return false;
  }

  // 1. Try modern Clipboard API (available in Secure Contexts: HTTPS or localhost)
  if (
    typeof window !== "undefined" &&
    window.isSecureContext &&
    typeof navigator !== "undefined" &&
    navigator.clipboard &&
    typeof navigator.clipboard.writeText === "function"
  ) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (err) {
      console.warn("navigator.clipboard.writeText failed, falling back to textarea execCommand:", err);
    }
  }

  // 2. Fallback to hidden textarea with document.execCommand('copy') (works on HTTP / non-secure contexts)
  if (typeof document !== "undefined") {
    try {
      const textArea = document.createElement("textarea");
      textArea.value = text;
      // Prevent scrolling to bottom of page on iOS / mobile / desktop
      textArea.style.position = "fixed";
      textArea.style.top = "0";
      textArea.style.left = "0";
      textArea.style.width = "2em";
      textArea.style.height = "2em";
      textArea.style.padding = "0";
      textArea.style.border = "none";
      textArea.style.outline = "none";
      textArea.style.boxShadow = "none";
      textArea.style.background = "transparent";
      textArea.style.opacity = "0";
      textArea.setAttribute("readonly", "");

      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      textArea.setSelectionRange(0, textArea.value.length);

      const successful = document.execCommand("copy");
      document.body.removeChild(textArea);
      return successful;
    } catch (err) {
      console.error("document.execCommand('copy') fallback failed:", err);
      return false;
    }
  }

  return false;
}
