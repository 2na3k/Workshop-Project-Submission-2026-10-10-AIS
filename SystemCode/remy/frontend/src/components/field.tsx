export default function Field({
  id,
  label,
  type = "text",
  autoComplete,
  placeholder,
  required = true,
}: {
  id: string;
  label: string;
  type?: "text" | "email" | "password";
  autoComplete?: string;
  placeholder?: string;
  required?: boolean;
}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-bold">
        {label}
      </label>
      <input
        id={id}
        name={id}
        type={type}
        autoComplete={autoComplete}
        placeholder={placeholder}
        required={required}
        className="w-full rounded-xl border border-subtle bg-background px-3.5 py-2.5 text-sm outline-none transition placeholder:text-muted/60 focus:border-accent focus:ring-2 focus:ring-accent/20"
      />
    </div>
  );
}
