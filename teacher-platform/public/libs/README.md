## 说明

讯飞 **Avatar SDK** 已改为放在 **`src/libs/avatar-sdk-web_3.1.2.1002/`**，由 Vite 打包。

**不要**再把 SDK 放在 `public/` 下并用 `import()` 加载——Vite 会报错（`public` 仅能通过 URL 直链或 HTML `<script src>` 引用）。

原下载包仍可保留在仓库其它位置作参考；运行时使用 `src/libs` 中的副本即可。
