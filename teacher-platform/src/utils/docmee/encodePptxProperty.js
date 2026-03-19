function uint8ArrayToBase64(bytes) {
  let binary = ''
  const chunkSize = 0x8000
  for (let i = 0; i < bytes.length; i += chunkSize) {
    const chunk = bytes.subarray(i, i + chunkSize)
    binary += String.fromCharCode(...chunk)
  }
  return window.btoa(binary)
}

async function gzipText(text) {
  if (typeof CompressionStream === 'undefined') {
    throw new Error('当前浏览器不支持 Gzip 压缩，无法保存 PPT 编辑结果')
  }

  const stream = new Blob([text]).stream().pipeThrough(new CompressionStream('gzip'))
  const buffer = await new Response(stream).arrayBuffer()
  return new Uint8Array(buffer)
}

export async function encodePptxProperty(doc) {
  const json = JSON.stringify(doc)
  const gzipBytes = await gzipText(json)
  return uint8ArrayToBase64(gzipBytes)
}
