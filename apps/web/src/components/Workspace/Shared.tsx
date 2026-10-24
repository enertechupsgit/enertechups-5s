import { useEffect, useRef, useState, type ReactNode } from "react";
import { X, Upload, ImagePlus, CircleDashed } from "lucide-react";
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
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const [error, setError] = useState("");
  return (
    <div>
      <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-dashed border-base-300 bg-base-200/50 p-4">
        {value ? (
          <img
            className="h-12 w-16 rounded object-cover"
            src={value}
            alt="Selected evidence"
          />
        ) : (
          <ImagePlus className="text-base-content/40" size={25} />
        )}
        <span className="flex-1">
          <span className="block text-xs font-medium">
            {value
              ? "Evidence attached · replace photo"
              : "Take a photo or upload evidence"}
          </span>
          <span className="mt-1 block text-[10px] text-base-content/60">
            JPEG, PNG or WebP · up to 3 MB · local development storage
          </span>
        </span>
        <Upload size={15} />
        <input
          className="sr-only"
          aria-label="Upload evidence photo"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          capture="environment"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (!file) return;
            if (
              !["image/jpeg", "image/png", "image/webp"].includes(file.type) ||
              file.size > 3 * 1024 * 1024
            ) {
              setError("Choose a JPEG, PNG or WebP photo under 3 MB.");
              return;
            }
            setError("");
            const reader = new FileReader();
            reader.onload = () => onChange(String(reader.result));
            reader.onerror = () =>
              setError("Could not read this photo. Try again.");
            reader.readAsDataURL(file);
          }}
        />
      </label>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
