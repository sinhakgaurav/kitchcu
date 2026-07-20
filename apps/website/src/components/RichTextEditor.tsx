import { useCallback, useEffect, useRef, useState } from "react";
import { uploadKitchenMedia, type MediaUploadContext } from "../lib/api";
import { sanitizeHtml } from "../shared/sanitizeHtml";

type Props = {
  value: string;
  onChange: (html: string) => void;
  placeholder?: string;
  minHeight?: number;
  /** When set, enables inline image upload via kitchen media API. */
  kitchenId?: string;
  uploadContext?: MediaUploadContext;
  disabled?: boolean;
};

export function RichHtml({ html, className = "" }: { html: string; className?: string }) {
  const trimmed = html.trim();
  if (!trimmed) return null;
  const isHtml = /<[a-z][\s\S]*>/i.test(trimmed);
  if (!isHtml) {
    return <p className={className}>{trimmed}</p>;
  }
  const safe = sanitizeHtml(trimmed);
  if (!safe) return null;
  return (
    <div
      className={`rich-content${className ? ` ${className}` : ""}`}
      dangerouslySetInnerHTML={{ __html: safe }}
    />
  );
}

const COMMANDS: { label: string; command: string; value?: string }[] = [
  { label: "B", command: "bold" },
  { label: "I", command: "italic" },
  { label: "• List", command: "insertUnorderedList" },
  { label: "1. List", command: "insertOrderedList" },
  { label: "H3", command: "formatBlock", value: "h3" },
];

function normalizeHtml(html: string): string {
  const trimmed = html.trim();
  if (!trimmed || trimmed === "<br>" || trimmed === "<div><br></div>") return "";
  return html;
}

export function RichTextEditor({
  value,
  onChange,
  placeholder,
  minHeight = 120,
  kitchenId,
  uploadContext = "general",
  disabled = false,
}: Props) {
  const editorRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");

  const canUploadImage = Boolean(kitchenId) && !disabled;

  useEffect(() => {
    const el = editorRef.current;
    if (!el || el.innerHTML === value) return;
    el.innerHTML = value || "";
  }, [value]);

  const emitChange = useCallback(() => {
    const html = editorRef.current?.innerHTML ?? "";
    onChange(normalizeHtml(html));
  }, [onChange]);

  const runCommand = (command: string, commandValue?: string) => {
    if (disabled) return;
    editorRef.current?.focus();
    document.execCommand(command, false, commandValue);
    emitChange();
  };

  const addLink = () => {
    if (disabled) return;
    const url = window.prompt("Link URL (https://…)");
    if (!url) return;
    runCommand("createLink", url);
  };

  const insertImageAtCursor = (url: string) => {
    const editor = editorRef.current;
    if (!editor) return;
    editor.focus();
    const img = document.createElement("img");
    img.src = url;
    img.alt = "";
    img.className = "rich-editor__img";
    img.loading = "lazy";

    const selection = window.getSelection();
    if (selection && selection.rangeCount > 0) {
      const range = selection.getRangeAt(0);
      if (editor.contains(range.commonAncestorContainer)) {
        range.deleteContents();
        range.insertNode(img);
        const spacer = document.createTextNode("\u00a0");
        img.after(spacer);
        range.setStartAfter(spacer);
        range.collapse(true);
        selection.removeAllRanges();
        selection.addRange(range);
        emitChange();
        return;
      }
    }

    editor.appendChild(img);
    editor.appendChild(document.createElement("br"));
    emitChange();
  };

  const onImageSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || !kitchenId) return;
    if (!file.type.startsWith("image/")) {
      setUploadError("Please choose an image file.");
      return;
    }

    setUploadError("");
    setUploading(true);
    try {
      const result = await uploadKitchenMedia(kitchenId, file, {
        context: uploadContext,
        is_live_capture: false,
        filename: file.name || "inline.jpg",
      });
      insertImageAtCursor(result.url);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Image upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className={`rich-editor${disabled ? " rich-editor--disabled" : ""}`}>
      <div className="rich-editor__toolbar" role="toolbar" aria-label="Formatting">
        {COMMANDS.map((item) => (
          <button
            key={item.label}
            type="button"
            className="rich-editor__btn"
            disabled={disabled}
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => runCommand(item.command, item.value)}
          >
            {item.label}
          </button>
        ))}
        <button
          type="button"
          className="rich-editor__btn"
          disabled={disabled}
          onMouseDown={(e) => e.preventDefault()}
          onClick={addLink}
        >
          Link
        </button>
        {canUploadImage && (
          <>
            <button
              type="button"
              className="rich-editor__btn rich-editor__btn--image"
              disabled={uploading}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => fileInputRef.current?.click()}
            >
              {uploading ? "Uploading…" : "Image"}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif"
              className="rich-editor__file"
              tabIndex={-1}
              aria-hidden
              onChange={onImageSelected}
            />
          </>
        )}
      </div>
      <div
        ref={editorRef}
        className="rich-editor__body"
        contentEditable={!disabled}
        role="textbox"
        aria-multiline="true"
        data-placeholder={placeholder}
        style={{ minHeight }}
        onInput={emitChange}
        onBlur={emitChange}
      />
      {uploadError && <p className="rich-editor__error">{uploadError}</p>}
    </div>
  );
}
