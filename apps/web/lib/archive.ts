import { unzip } from "fflate";

const MAX_PREVIEW_BYTES = 20 * 1024 * 1024;
const MAX_COMPRESSION_RATIO = 200;

function contentType(filename: string) {
  const suffix = filename.toLowerCase().split(".").pop();
  if (suffix === "pdf") return "application/pdf";
  if (suffix === "png") return "image/png";
  return "image/jpeg";
}

export async function extractArchiveMember(archive: File, memberName: string): Promise<File> {
  const input = new Uint8Array(await archive.arrayBuffer());
  let rejection = "";
  const entries = await new Promise<Record<string, Uint8Array>>((resolve, reject) => {
    unzip(input, {
      // Filtering happens from ZIP metadata before decompression, so opening a
      // result never inflates unrelated members or an oversized preview.
      filter: (entry) => {
        if (entry.name !== memberName) return false;
        if (entry.originalSize > MAX_PREVIEW_BYTES) {
          rejection = "压缩包内文件超过 20 MB，无法在浏览器预览。";
          return false;
        }
        if (entry.originalSize / Math.max(entry.size, 1) > MAX_COMPRESSION_RATIO) {
          rejection = "压缩包内文件的压缩比异常，已停止浏览器预览。";
          return false;
        }
        return true;
      },
    }, (error, data) => error ? reject(error) : resolve(data));
  });

  if (rejection) throw new Error(rejection);
  const content = entries[memberName];
  if (!content) throw new Error("无法从本地 ZIP 中读取这份原文。");
  const filename = memberName.split("/").pop() ?? memberName;
  const browserOwned = new Uint8Array(content.byteLength);
  browserOwned.set(content);
  return new File([browserOwned.buffer], filename, { type: contentType(memberName) });
}
