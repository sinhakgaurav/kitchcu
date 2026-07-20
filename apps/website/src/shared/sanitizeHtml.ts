/** Client-side HTML sanitizer for owner-authored rich content (defense in depth). */

const ALLOWED = new Set(["P", "STRONG", "EM", "B", "I", "UL", "OL", "LI", "BR", "H3", "A"]);

export function sanitizeHtml(input: string): string {
  const trimmed = input.trim();
  if (!trimmed) return "";
  if (typeof document === "undefined") {
    return trimmed.replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, "");
  }
  const template = document.createElement("template");
  template.innerHTML = trimmed;
  const walk = (node: Node) => {
    const children = Array.from(node.childNodes);
    for (const child of children) {
      if (child.nodeType === Node.ELEMENT_NODE) {
        const el = child as HTMLElement;
        if (!ALLOWED.has(el.tagName)) {
          el.replaceWith(...Array.from(el.childNodes));
          continue;
        }
        for (const attr of Array.from(el.attributes)) {
          const name = attr.name.toLowerCase();
          if (name.startsWith("on") || name === "style") {
            el.removeAttribute(attr.name);
            continue;
          }
          if (el.tagName === "A" && name === "href") {
            const href = attr.value.trim();
            if (!/^https?:\/\//i.test(href)) {
              el.removeAttribute("href");
            } else {
              el.setAttribute("rel", "noopener noreferrer");
              el.setAttribute("target", "_blank");
            }
          } else if (name !== "href") {
            el.removeAttribute(attr.name);
          }
        }
        walk(el);
      } else if (child.nodeType === Node.COMMENT_NODE) {
        child.parentNode?.removeChild(child);
      }
    }
  };
  walk(template.content);
  return template.innerHTML.trim();
}
