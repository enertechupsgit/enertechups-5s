// API timestamps without an offset are UTC; plain dates remain calendar dates.
export function parseDate(value: string): Date {
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return new Date(`${value}T00:00:00`);
  return new Date(/(?:Z|[+-]\d{2}:?\d{2})$/i.test(value) ? value : `${value}Z`);
}
export const timestamp = (value: string) => parseDate(value).getTime();
export const dateLabel = (value?: string | null) =>
  value
    ? parseDate(value).toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
      })
    : "No due date";
export const dateTimeLabel = (value: string) =>
  parseDate(value).toLocaleString("en-IN");
