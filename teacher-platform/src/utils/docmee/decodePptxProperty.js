function base64ToUint8Array(base64) {
  const binary = window.atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes
}

async function gunzipToText(bytes) {
  if (typeof DecompressionStream === 'undefined') {
    throw new Error('当前浏览器不支持 Gzip 解压，无法预览 PPT')
  }

  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))
  return new Response(stream).text()
}

export async function decodePptxProperty(encoded) {
  if (!encoded) return null
  const bytes = base64ToUint8Array(encoded)
  const text = await gunzipToText(bytes)
  return JSON.parse(text)
}
