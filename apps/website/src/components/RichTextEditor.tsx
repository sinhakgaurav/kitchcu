import { useCallback, useEffect, useRef } from "react";

type Props = {
  value: string;
  onChange: (html: string) => void;
  placeholder?: string;
  minHeight?: number;
};

const COMMANDS: { label: string; command: string; value?: string }[] = [
  { label: "B", command: "bold" },
  { label: "I", command: "italic" },
  { label: "• List", command: "insertUnorderedList" },
  { label: "1. List", command: "insertOrderedList" },
  { label: "H3", command: "formatBlock", value: "h3" },
];

export function RichTextEditor({ value, onChange, placeholder, minHeight = 120 }: Props) {
  const editorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = editorRef.current;
    if (!el || el.innerHTML === value) return;
    el.innerHTML = value || "";
  }, [value]);

  const emitChange = useCallback(() => {
    const html = editorRef.current?.innerHTML ?? "";
    onChange(html === "<br>" ? "" : html);
  }, [onChange]);

  const runCommand = (command: string, commandValue?: string) => {
    editorRef.current?.focus();
    document.execCommand(command, false, commandValue);
    emitChange();
  };

  const addLink = () => {
    const url = window.prompt("Link URL (https://…)");
    if (!url) return;
    runCommand("createLink", url);
  };

  return (
    <div className="rich-editor">
      <div className="rich-editor__toolbar" role="toolbar" aria-label="Formatting">
        {COMMANDS.map((item) => (
          <button
            key={item.label}
            type="button"
            className="rich-editor__btn"
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => runCommand(item.command, item.value)}
          >
            {item.label}
          </button>
        ))}
        <button type="button" className="rich-editor__btn" onMouseDown={(e) => e.preventDefault()} onClick={addLink}>
          Link
        </button>
      </div>
      <div
        ref={editorRef}
        className="rich-editor__body"
        contentEditable
        role="textbox"
        aria-multiline="true"
        data-placeholder={placeholder}
        style={{ minHeight }}
        onInput={emitChange}
        onBlur={emitChange}
      />
    </div>
  );
}
