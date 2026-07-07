### 3. [x] PDF 导出 UTF-8 解码错误 — `rfile.read(n)` 不保证一次读完

**现象**：服务器部署后 PDF 下载报错 `'utf-8' codec can't decode bytes`。本机 localhost 正常。

**根因**：Python `http.server` 的 `rfile.read(n)` 返回最多 n 字节，不保证一次读完。nginx 代理下大 POST body 被分片，只读到部分字节，后续字节混入下次请求产生非法 UTF-8 序列。

**修复**（3 处）：
1. `_read_body()` — 循环读取直到收齐 Content-Length 全部字节
2. 新增 `_parse_post_body()` — 统一解析 JSON/form POST，latin-1 容错
3. `_export_pdf()` / `_export_doc()` — 改用 `_parse_post_body()`

**修复版本**：commit `45c75c9`
