import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";

// Fail before packaging if the deployed hash diverges from the compiled proxy.
const root = new URL("../", import.meta.url);
const source = await readFile(new URL("electron/services/vivox-client.ts", root), "utf8");
const expected = source.match(/export const VIVOX_PROXY_SHA256\s*=\s*"([a-f0-9]{64})"/)?.[1];
const sidecar = (await readFile(new URL("resources/patches/vivoxsdk_x64.dll.sha256", root), "utf8")).trim().split(/\s+/)[0];
const actual = createHash("sha256").update(await readFile(new URL("resources/patches/vivoxsdk_x64.dll", root))).digest("hex");
if (actual !== expected || actual !== sidecar) {
  throw new Error(`Vivox proxy mismatch: binary=${actual}, launcher=${expected}, sidecar=${sidecar}`);
}
console.log(`Vivox proxy agrees with launcher and sidecar: ${actual}`);
