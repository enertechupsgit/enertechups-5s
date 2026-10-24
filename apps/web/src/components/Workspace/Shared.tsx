import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { X, Camera, CircleDashed } from "lucide-react";
export function Status({ value }: { value: string }) {
  const map: Record<string, [string, string]> = {
    draft: ["Draft", "badge-ghost"],
    assigned: ["Open", "badge-info badge-soft"],
    in_progress: ["In progress", "badge-info badge-soft"],
    submitted_for_review: ["Needs review", "badge-warning badge-soft"],
    rejected: ["Changes requested", "badge-error badge-soft"],
    completed: ["Completed", "badge-success badge-soft"],
    approved: ["Approved", "badge-success badge-soft"],
    online: ["Online", "badge-success badge-soft"],
    offline: ["Offline", "badge-error badge-soft"],
    maintenance: ["Maintenance", "badge-warning badge-soft"],
  };
  const [text, cls] = map[value] || [value.replaceAll("_", " "), "badge-ghost"];
  return (
    <span className={`badge ${cls}`}>
      <i className="status-dot" />
      {text}
    </span>
  );
}
export function Empty({
  title,
  text,
  action,
}: {
  title: string;
  text: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <CircleDashed size={32} strokeWidth={1.3} />
      <h3>{title}</h3>
      <p>{text}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
export function Dialog({
  title,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const el = ref.current;
    el?.showModal();
    return () => el?.close();
  }, []);
  return (
    <dialog ref={ref} className="modal" onCancel={onClose} aria-label={title}>
      <div className={`modal-box ${wide ? "max-w-3xl!" : ""}`}>
        <div className="dialog-head">
          <h2>{title}</h2>
          <button
            className="btn btn-ghost btn-square"
            onClick={onClose}
            aria-label="Close dialog"
          >
            <X />
          </button>
        </div>
        {children}
      </div>
      <form method="dialog" className="modal-backdrop">
        <button onClick={onClose}>Close</button>
      </form>
    </dialog>
  );
}
export function EvidenceInput({
  value,
  onChange,
  label = "Evidence photo",
  onPendingChange,
}: {
  value: string;
  onChange: (value: string) => void;
  label?: string;
  onPendingChange?: (pending: boolean) => void;
}) {
  const id = useId();
  const camera = useRef<HTMLInputElement>(null);
  const [error, setError] = useState("");
  const [reading, setReading] = useState(false);
  async function select(file?: File) {
    if (!file) return;
    if (
      !["image/jpeg", "image/png", "image/webp"].includes(file.type) ||
      file.size > 3 * 1024 * 1024 ||
      !file.size
    ) {
      setError("Choose a JPEG, PNG or WebP photo up to 3 MB.");
      return;
    }
    setReading(true);
    onPendingChange?.(true);
    setError("");
    const url = URL.createObjectURL(file);
    try {
      await new Promise<void>((resolve, reject) => {
        const picture = new window.Image();
        picture.onload = () =>
          picture.naturalWidth * picture.naturalHeight <= 20000000
            ? resolve()
            : reject(new Error("Choose a photo up to 20 megapixels."));
        picture.onerror = () =>
          reject(
            new Error("This photo could not be read. Choose another image."),
          );
        picture.src = url;
      });
      const data = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result));
        reader.onerror = () =>
          reject(new Error("Could not read this photo. Try again."));
        reader.readAsDataURL(file);
      });
      onChange(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      URL.revokeObjectURL(url);
      setReading(false);
      onPendingChange?.(false);
    }
  }
  return (
    <div className="evidence-input my-3">
      <label htmlFor={id} className="block mb-2 text-xs font-medium">
        {label}
      </label>
      <div className="flex flex-wrap gap-2 items-center">
        <input
          id={id}
          className="file-input w-full min-w-0 flex-1"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          aria-describedby={`${id}-help ${id}-error`}
          disabled={reading}
          onChange={(event) => {
            void select(event.target.files?.[0]);
            event.target.value = "";
          }}
        />
        <button
          type="button"
          className="btn btn-square"
          aria-label={`Take ${label.toLowerCase()}`}
          disabled={reading}
          onClick={() => camera.current?.click()}
        >
          <Camera size={18} />
        </button>
        <input
          ref={camera}
          className="sr-only"
          aria-hidden="true"
          tabIndex={-1}
          aria-label={`Camera for ${label.toLowerCase()}`}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          capture="environment"
          disabled={reading}
          onChange={(event) => {
            void select(event.target.files?.[0]);
            event.target.value = "";
          }}
        />
      </div>
      <p id={`${id}-help`} className="mt-2 text-xs text-base-content/60">
        JPEG, PNG or WebP · up to 3 MB
      </p>
      {reading && (
        <p role="status" className="mt-2 text-sm">
          Reading photo…
        </p>
      )}
      {value && (
        <div className="mt-3 flex items-center gap-3 rounded-lg border border-base-300 p-2">
          <img
            className="h-16 w-24 rounded object-contain"
            src={value}
            alt={`${label} preview`}
          />
          <span className="text-xs flex-1">Photo attached</span>
          <button
            className="btn btn-ghost btn-square"
            type="button"
            disabled={reading}
            aria-label={`Remove ${label.toLowerCase()}`}
            onClick={() => {
              onChange("");
              setError("");
            }}
          >
            <X size={16} />
          </button>
        </div>
      )}
      <div id={`${id}-error`} aria-live="polite">
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}
