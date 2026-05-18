const API = "";

export async function api(path, options) {
  const r = await fetch(`${API}${path}`, options);
  if (!r.ok) {
    const text = await r.text();
    let detail = text;
    try {
      detail = JSON.parse(text).detail ?? text;
    } catch {
      /* */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return r.json();
}
