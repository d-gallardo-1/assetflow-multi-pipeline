/** A refused command, in the server's own words. */
export function ErrorNote({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p role="alert" className="rounded-md border border-critical/50 bg-critical/10 px-3 py-2 text-sm text-critical">
      {message}
    </p>
  );
}
