// frontend/e2e/helpers/files.ts

// A valid 1x1 transparent PNG (67 bytes) — used as the ID-card upload.
const TINY_PNG_BASE64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==";

export function tinyPngBuffer(): Buffer {
  return Buffer.from(TINY_PNG_BASE64, "base64");
}

/** Payload for `locator.setInputFiles()` / APIRequestContext `multipart`. */
export function tinyPngFile(name = "id-card.png") {
  return { name, mimeType: "image/png", buffer: tinyPngBuffer() };
}
