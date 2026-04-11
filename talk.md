 目标风格：
  - 温暖、轻盈、奶油感、毛玻璃
  - 不是科技感深色，也不是高饱和炫彩
  - 背景应像高级产品首页，而不是普通表单页
  - 视觉关键词：soft pastel, glassmorphism, creamy light, warm gradient, subtle glow

  背景要求：
  - 整页使用一个大面积线性渐变
  - 主渐变方向约 145deg
  - 颜色从暖奶油色过渡到浅粉、浅紫、浅蓝
  - 推荐渐变色：
    - #fff4dc
    - #fff9f2
    - #fdf1ff
    - #eff7ff
  - 左上添加一个大号橙色模糊光斑
    - rgba(249, 115, 22, 0.28)
  - 右上添加一个大号粉色模糊光斑
    - rgba(236, 72, 153, 0.22)
  - 光斑必须是 radial-gradient，并且边缘完全透明
  - 页面上的内容卡片要用半透明白色背景
    - rgba(255,255,255,0.78)
  - 卡片要带 backdrop-filter: blur(18px~22px)
  - 阴影要大而软，不能重黑
  - 整体观感要柔和、明亮、干净、偏产品化

  限制：
  - 不要深色背景
  - 不要赛博朋克
  - 不要高对比霓虹
  - 不要复杂纹理
  - 不要紫色主导，暖色要更明显
这个背景不是图片生成的，是纯 CSS 叠出来的，关键在 teacher-platform/src/views/rehearsal/RehearsalLab.vue:278。

  核心做法是：

  - 底层一条暖白到粉紫再到浅蓝的 linear-gradient
  - 左上一个橙色发光团
  - 右上一个粉色发光团
  - 上层卡片用半透明白色 + backdrop-filter: blur(...) 做毛玻璃

  当前实际配色大致是：

  background: linear-gradient(145deg, #fff4dc 0%, #fff9f2 28%, #fdf1ff 62%, #eff7ff 100%);

  叠加两个光斑：

  background: radial-gradient(circle, rgba(249, 115, 22, 0.28), transparent 72%);
  background: radial-gradient(circle, rgba(236, 72, 153, 0.22), transparent 74%);