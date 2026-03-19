# 文多多AiPPT开放平台API文档

## 目录
- [接入流程](#接入流程)
- [接口鉴权](#接口鉴权)
- [API接口分类](#api接口分类)
  - [AI PPT - V2](#ai-ppt---v2)
  - [AI PPT - V1](#ai-ppt---v1)
  - [模板管理](#模板管理)
  - [PPT获取与操作](#ppt获取与操作)
  - [积分和使用记录](#积分和使用记录)
  - [其他接口](#其他接口)
- [错误码](#错误码)
- [特殊说明](#特殊说明)

## 接入流程

文多多AiPPT API接入遵循标准的RESTful设计模式，主要流程如下：

1. **获取API Key**：在[开放平台](https://open.docmee.cn/open)注册账号并获取API Key。
2. **创建访问Token**：通过`createApiToken`接口创建具有时效性的访问Token。
3. **调用业务接口**：在请求头中携带Token调用具体的业务接口。
4. **处理响应**：根据接口返回的数据进行后续处理。

> **重要提示**：该接口请在服务端调用，同一个uid创建token时，之前通过该uid创建的token会在10秒内过期。

## 接口鉴权

### 创建接口Token

用于生成调用鉴权Token，支持限制生成次数与数据隔离。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/user/createApiToken` |
| 请求方法 | POST |
| 请求头 | `Content-Type: application/json`, `Api-Key: xxx` |

#### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| uid | string | 否 | 用户ID（自定义用户ID，非必填，建议不超过32位字符串），不同uid创建的token数据会相互隔离，主要用于数据隔离 |
| limit | number | 否 | 限制token最大生成PPT次数（数字，为空则不限制，为0时不允许生成PPT，大于0时限制生成PPT次数）。UI iframe接入时强烈建议传limit参数，避免token泄露造成损失！ |
| timeOfHours | number | 否 | 过期时间，单位：小时，默认两小时过期，最大可设置为48小时 |

#### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| data.token | string | token (调用api接口鉴权用，请求头传token) |
| data.expireTime | number | 过期时间（秒） |
| code | number | 状态码 |
| message | string | 提示信息 |

#### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/user/createApiToken' \
--header 'Content-Type: application/json' \
--header 'Api-Key: xxx' \
--data '{"uid": "xxx","limit": 10}'
```

### API接口鉴权

所有业务接口都需要进行鉴权。

| 属性 | 说明 |
|------|------|
| 请求头 | `token: {token}` 或直接使用 `Api-Key: {apiKey}` |

#### 接口请求示例
```bash
curl --location 'https://open.docmee.cn/api/ppt/xxx' \
--header 'token: xxx'
```

> **注意**：封面图片资源访问，需要在url上拼接`?token=xxx`。

## API接口分类

### AI PPT - V2

官方推荐使用的最新版本API。

#### 创建任务

开启一个生成PPT的任务。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/v2/createTask` |
| 请求方法 | POST |
| Content-Type | `multipart/form-data` |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| type | number | 是 | 类型：<br>1. 智能生成（主题、要求）<br>2. 上传文件生成<br>3. 上传思维导图生成<br>4. 通过word精准转ppt<br>5. 通过网页链接生成<br>6. 粘贴文本内容生成<br>7. Markdown大纲生成 |
| content | string | 否 | 内容：<br>- type=1：用户输入主题或要求（不超过1000字符）<br>- type=2,4：不传<br>- type=3：幕布等分享链接<br>- type=5：网页链接地址（http/https）<br>- type=6：粘贴文本内容（不超过20000字符）<br>- type=7：大纲内容（markdown） |
| file | File[] | 否 | 文件列表（文件数不超过5个，总大小不超过50M）：<br>- type=1：上传参考文件（非必传，支持多个）<br>- type=2：上传文件（支持多个）<br>- type=3：上传思维导图（xmind/mm/md）（仅支持一个）<br>- type=4：上传word文件（仅支持一个）<br>- type=5,6,7：不传 |

**支持格式**：doc/docx/pdf/ppt/pptx/txt/md/xls/xlsx/csv/html/epub/mobi/xmind/mm

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| data.id | string | 任务ID |
| code | number | 状态码 |
| message | string | 提示信息 |

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/ppt/v2/createTask' \
--header 'Content-Type: multipart/form-data' \
--form 'type=1' \
--form 'content="AI未来的发展"'
```

#### 获取生成选项

获取调用生成大纲内容需要使用的相关选项。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/v2/options` |
| 请求方法 | GET |

> 该接口支持国际化，URL携带lang参数指定。

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| data.lang | array | 语种选项 |
| data.scene | array | 场景选项 |
| data.audience | array | 受众选项 |
| code | number | 状态码 |
| message | string | 提示信息 |

**语种(lang)选项**：
1. {name: "简体中文", value: "zh"}
2. {name: "繁體中文", value: "zh-Hant"}
3. {name: "English", value: "en"}
4. {name: "日本語", value: "ja"}
5. {name: "한국어", value: "ko"}
6. {name: "Français", value: "fr"}
7. {name: "Русский", value: "ru"}
8. {name: "العربية", value: "ar"}
9. {name: "Deutsch", value: "de"}
10. {name: "Español", value: "es"}
11. {name: "Italiano", value: "it"}
12. {name: "Português", value: "pt"}

**场景(scene)选项**：
1. {name: "通用场景", value: "通用场景"}
2. {name: "教学课件", value: "教学课件"}
3. {name: "工作总结", value: "工作总结"}
4. {name: "工作计划", value: "工作计划"}
5. {name: "项目汇报", value: "项目汇报"}
6. {name: "解决方案", value: "解决方案"}
7. {name: "研究报告", value: "研究报告"}
8. {name: "会议材料", value: "会议材料"}
9. {name: "产品介绍", value: "产品介绍"}
10. {name: "公司介绍", value: "公司介绍"}
11. {name: "商业计划书", value: "商业计划书"}
12. {name: "科普宣传", value: "科普宣传"}
13. {name: "公众演讲", value: "公众演讲"}

**受众(audience)选项**：
1. {name: "大众", value: "大众"}
2. {name: "学生", value: "学生"}
3. {name: "老师", value: "老师"}
4. {name: "上级领导", value: "上级领导"}
5. {name: "下属", value: "下属"}
6. {name: "面试官", value: "面试官"}
7. {name: "同事", value: "同事"}

##### 请求示例
```bash
curl -X GET --location 'https://open.docmee.cn/api/ppt/v2/options?lang=zh'
```

#### 生成大纲内容

生成当前任务的大纲及内容。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/v2/generateContent` |
| 请求方法 | POST |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| id | string | 是 | 任务ID |
| stream | boolean | 否 | 是否流式（默认true） |
| length | string | 否 | 篇幅长度：short/medium/long => 10-15页/20-30页/25-35页 |
| scene | string | 否 | 演示场景：通用场景、教学课件、工作总结、工作计划、项目汇报、解决方案、研究报告、会议材料、产品介绍、公司介绍、商业计划书、科普宣传、公众演讲等任意场景类型 |
| audience | string | 否 | 受众：大众、学生、老师、上级领导、下属、面试官、同事等任意受众类型 |
| lang | string | 否 | 语言: zh/zh-Hant/en/ja/ko/ar/de/fr/it/pt/es/ru |
| prompt | string | 否 | 用户要求（小于50字） |

> **特别提醒**：参数`prompt`只会在创建的任务类型为1(智能生成), 2(上传文件生成), 5(通过网页链接生成), 6(粘贴文本内容生成)这些类型时生效，其他类型会忽略该字段。

##### 响应
**流式响应(event-stream)**：
```json
{"text": "#", "status": 3}
{"text": " ", "status": 3}
{"text": "主题", "status": 3}
...
{
  "text": "",
  "status": 4,
  "result": {
    "level": 1,
    "name": "主题",
    "children": [
      {
        "level": 2,
        "name": "章节",
        "children": [
          {
            "level": 3,
            "name": "页面标题",
            "children": [
              {
                "level": 4,
                "name": "内容标题",
                "children": [
                  {
                    "level": 0,
                    "name": "内容"
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  }
}
```

**非流式响应(application/json)**：
```json
{
  "code": 0,
  "data": {
    "text": "# 主题\\n## 章节\\n### 页面标题\\n#### 内容标题\\n- 内容",
    "result": {
      "level": 1,
      "name": "主题",
      "children": [
        {
          "level": 2,
          "name": "章节",
          "children": [
            {
              "level": 3,
              "name": "页面标题",
              "children": [
                {
                  "level": 4,
                  "name": "内容标题",
                  "children": [
                    {
                      "level": 0,
                      "name": "内容"
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  },
  "message": "ok"
}
```

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/ppt/v2/generateContent' \
--header 'Content-Type: application/json' \
--header 'token: {token}' \
--data '{"id":"xxx","stream":true,"length":"medium"}'
```

#### 修改大纲内容

根据用户指令修改大纲内容。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/v2/updateContent` |
| 请求方法 | POST |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| id | string | 是 | 任务ID |
| stream | boolean | 否 | 是否流式（默认true） |
| markdown | string | 是 | 大纲内容markdown |
| question | string | 否 | 用户修改建议 |

##### 响应
event-stream或application/json，结构同生成大纲内容。

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/ppt/v2/updateContent' \
--header 'Content-Type: application/json' \
--header 'token: {token}' \
--data '{"id":"xxx","markdown":"# 主题\\n## 章节","question":"帮我优化一下结构"}'
```

#### 生成PPT

根据markdown格式的PPT大纲与内容生成PPT作品。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/v2/generatePptx` |
| 请求方法 | POST |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| id | string | 是 | 任务ID |
| templateId | string | 是 | 模板ID（调用模板接口获取） |
| markdown | string | 是 | 大纲内容markdown |

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| data.pptInfo.id | string | ppt id |
| data.pptInfo.subject | string | 主题 |
| data.pptInfo.coverUrl | string | 封面 |
| data.pptInfo.templateId | string | 模板ID |
| data.pptInfo.pptxProperty | string | PPT数据结构（json gzip base64） |
| data.pptInfo.userId | string | 用户ID |
| data.pptInfo.userName | string | 用户名称 |
| data.pptInfo.companyId | number | 公司ID |
| data.pptInfo.updateTime | string/null | 更新时间 |
| data.pptInfo.createTime | string | 创建时间 |
| code | number | 状态码 |
| message | string | 提示信息 |

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/ppt/v2/generatePptx' \
--header 'Content-Type: application/json' \
--header 'token: {token}' \
--data '{"id":"xxx","templateId":"xxx","markdown":"# 主题\\n## 章节"}'
```

> 通过API生成PPT后，如果需要在前端进行编辑和渲染，推荐使用以下iframe方式编辑器：
> - github <https://github.com/veasion/aippt-ui-ppt-editor>
> - gitee <https://gitee.com/veasion/aippt-ui-ppt-editor>

### AI PPT - V1

旧版本API，仍可使用但推荐使用V2版本。

#### 解析文件内容

将若干支持的参数选项转化成dataUrl以便后续接口使用。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/parseFileData` |
| 请求方法 | POST |
| Content-Type | `multipart/form-data` |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| file | File | 否 | 文件（限制50M以内，最大解析2万字） |
| content | string | 否 | 用户粘贴文本内容 |
| fileUrl | string | 否 | 文件公网链接 |
| website | string | 否 | 网址（http/https） |
| websearch | string | 否 | 网络搜索关键词 |

**支持格式**：doc/docx/pdf/ppt/pptx/txt/md/xls/xlsx/csv/html/epub/mobi/xmind/mm

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| data.dataUrl | string | 文件数据url（有效期：当天） |
| code | number | 状态码 |
| message | string | 提示信息 |

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/ppt/parseFileData' \
--header 'Content-Type: multipart/form-data' \
--header 'token: {token}' \
--form 'file=@test.doc;filename=test.doc' \
--form 'content=文本内容' \
--form 'fileUrl=https://xxx.pdf' \
--form 'website=https://example.com' \
--form 'websearch=上海元符号智能科技有限公司'
```

#### 生成大纲

V1版本的生成大纲接口。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/generateOutline` |
| 请求方法 | POST |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| stream | boolean | 否 | 是否流式生成（默认流式） |
| length | string | 否 | 篇幅长度：short/medium/long, 默认medium, 分别对应: 10-15页/20-30页/25-35页 |
| lang | string | 否 | 语言: zh/zh-Hant/en/ja/ko/ar/de/fr/it/pt/es/ru |
| prompt | string | 否 | 用户要求（小于50字） |
| subject | string | 否 | 主题（与dataUrl可同时存在） |
| dataUrl | string | 否 | 文件数据url，通过解析文件内容接口返回（与subject可同时存在） |

##### 响应
```json
{"text": "", "status": 1}
{"text": "# ", "status": 3}
{"text": " ", "status": 3}
{"text": "主题", "status": 3}
...
{
  "text": "",
  "status": 4,
  "result": {
    "level": 1,
    "name": "主题",
    "children": [
      {
        "level": 2,
        "name": "章节",
        "children": [
          {
            "level": 3,
            "name": "页面标题",
            "children": [
              {
                "level": 4,
                "name": "内容标题"
              }
            ]
          }
        ]
      }
    ]
  }
}
```
> 状态：-1异常 1解析文件 3生成中 4完成

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/ppt/generateOutline' \
--header 'Content-Type: application/json' \
--header 'token: {token}' \
--data '{"subject": "AI未来的发展"}'
```

#### 修改大纲

根据用户指令修改大纲。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/ppt/updateOutline` |
| 请求方法 | POST |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| outlineMarkdown | string | 是 | 大纲markdown内容 |
| length | string | 否 | 篇幅长度：short/medium/long, 默认medium, 分别对应: 10-15页/20-30页/25-35页 |
| question | string | 否 | 用户修改建议<br>系统内置：用金字塔原理优化、强化大纲结构和过渡、突出大纲主题、让大纲更专业<br>用户自定义：比如"帮我把大纲改成金字塔结构" |

##### 响应
event-stream，结构同generateOutline生成大纲。

#### 生成大纲内容

通过Markdown格式的大纲生成PPT内容。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/generateContent` |
| 请求方法 | POST |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| stream | boolean | 否 | 是否流式生成（默认流式） |
| outlineMarkdown | string | 是 | 大纲markdown文本 |
| asyncGenPptx | boolean | 否 | 是否异步生成 |
| lang | string | 否 | 语言: zh/zh-Hant/en/ja/ko/ar/de/fr/it/pt/es/ru |
| prompt | string | 否 | 用户要求 |
| dataUrl | string | 否 | 文件数据url，调用解析文件内容接口返回 |

##### 响应
```json
{"text": "", "status": 3}
{"text": "#", "status": 3}
{"text": " ", "status": 3}
{"text": "主题", "status": 3}
...
{
  "text": "",
  "status": 4,
  "result": {
    "level": 1,
    "name": "主题",
    "children": [
      {
        "level": 2,
        "name": "章节",
        "children": [
          {
            "level": 3,
            "name": "页面标题",
            "children": [
              {
                "level": 4,
                "name": "内容标题",
                "children": [
                  {
                    "level": 0,
                    "name": "内容"
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  }
}
```
> 状态：-1异常 1解析文件 3生成中 4完成

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/ppt/generateContent' \
--header 'Content-Type: application/json' \
--header 'token: {token}' \
--data '{"outlineMarkdown": "xxx"}'
```

#### 生成PPT

通过大纲与内容生成PPT。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/generatePptx` |
| 请求方法 | POST |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| templateId | string | 否 | 模板ID（非必填） |
| pptxProperty | boolean | 否 | 是否返回PPT数据结构 |
| outlineContentMarkdown | string | 是 | 大纲内容markdown |
| notes | array | 否 | 备注（PPT页面备注，非必填，数组["内容页面一备注", "内容页面二备注"]） |

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| data.pptInfo.id | string | ppt id |
| data.pptInfo.subject | string | 主题 |
| data.pptInfo.coverUrl | string | 封面 |
| data.pptInfo.fileUrl | string | PPT文件 |
| data.pptInfo.templateId | string | 模板ID |
| data.pptInfo.pptxProperty | string | PPT数据结构（json数据通过gzip压缩base64编码返回） |
| data.pptInfo.userId | string | 用户ID |
| data.pptInfo.userName | string | 用户名称 |
| data.pptInfo.companyId | number | 公司ID |
| data.pptInfo.updateTime | string/null | 更新时间 |
| data.pptInfo.createTime | string | 创建时间 |
| code | number | 状态码 |
| message | string | 提示信息 |

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/ppt/generatePptx' \
--header 'Content-Type: application/json' \
--header 'token: {token}' \
--data '{"outlineContentMarkdown": "xxx", "pptxProperty": false}'
```

### Word 转 PPT

不同于通过解析文件生成PPT，Word转PPT会尽可能保留word文件中的层级结构和内容表述去生成PPT。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/v1/word2pptx` |
| 请求方法 | POST |
| Content-Type | `multipart/form-data` |

##### 请求参数
| 字段 | 类型 | 说明 |
|------|------|------|
| file | 文件 | docx文件（小于30M） |
| templateId | string | 模板ID（可空，为空时随机） |
| stream | boolean | 是否流式 |

##### 非流式响应(application/json)
```json
{
  "code": 0,
  "data": {
    "pptInfo": {
      "id": "xxx",
      "subject": "xxx",
      "coverUrl": "https://xxx.png",
      "fileUrl": "https://xxx.pptx",
      "templateId": "xxx",
      "pptxProperty": "xxx",
      "userId": "xxx",
      "userName": "xxx",
      "companyId": 1000,
      "updateTime": null,
      "createTime": "2024-01-01 10:00:00"
    }
  },
  "message": "操作成功"
}
```

##### 流式响应(event-stream)
```json
{"text": "", "status": 3}
{"text": "#", "status": 3}
{"text": " ", "status": 3}
{"text": "主题", "status": 3}
...
{"text": "", "status": 3, "pptId": "xxx"}
{
  "text": "",
  "status": 4,
  "result": {
    "id": "xxx",
    "subject": "xxx",
    "coverUrl": "https://xxx.png",
    "fileUrl": "https://xxx.pptx",
    "templateId": "xxx",
    "pptxProperty": "xxx",
    "userId": "xxx",
    "userName": "xxx",
    "companyId": 1000,
    "updateTime": null,
    "createTime": "2024-01-01 10:00:00"
  }
}
```
> 状态：-1异常 1解析文件 3生成中 4完成

##### 请求示例
```bash
# 非流式
curl -X POST --location 'https://open.docmee.cn/api/ppt/v1/word2pptx' \
--header 'Content-Type: multipart/form-data' \
--header 'token: {token}' \
--form 'stream=false' \
--form 'file=@test.docx;filename=test.docx'

# 流式
curl -X POST --location 'https://open.docmee.cn/api/ppt/v1/word2pptx' \
--header 'Content-Type: multipart/form-data' \
--header 'token: {token}' \
--form 'stream=true' \
--form 'file=@test.docx;filename=test.docx'
```

### 直接生成PPT

直接让模型生成PPT。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/directGeneratePptx` |
| 请求方法 | POST |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| stream | boolean | 否 | 是否流式生成 |
| templateId | string | 否 | 模板ID（非必填，为空则随机模板） |
| pptxProperty | boolean | 否 | 是否返回PPT数据结构 |
| length | string | 否 | 篇幅长度：short/medium/long, 默认medium, 分别对应: 10-15页/20-30页/25-35页 |
| lang | string | 否 | 语言: zh/zh-Hant/en/ja/ko/ar/de/fr/it/pt/es/ru |
| prompt | string | 否 | 用户要求（小于50字） |
| subject | string | 否 | 主题（与dataUrl可同时存在） |
| dataUrl | string | 否 | 文件数据url，调用解析文件内容接口返回（与subject可同时存在） |

##### 非流式响应(application/json)
```json
{
  "code": 0,
  "data": {
    "pptInfo": {
      "id": "xxx",
      "subject": "xxx",
      "coverUrl": "https://xxx.png",
      "fileUrl": "https://xxx.pptx",
      "templateId": "xxx",
      "pptxProperty": "xxx",
      "userId": "xxx",
      "userName": "xxx",
      "companyId": 1000,
      "updateTime": null,
      "createTime": "2024-01-01 10:00:00"
    }
  },
  "message": "操作成功"
}
```

##### 流式响应(event-stream)
```json
{"text": "", "status": 3}
{"text": "#", "status": 3}
{"text": " ", "status": 3}
{"text": "主题", "status": 3}
...
{"text": "", "status": 3, "pptId": "xxx"}
{
  "text": "",
  "status": 4,
  "result": {
    "id": "xxx",
    "subject": "xxx",
    "coverUrl": "https://xxx.png",
    "fileUrl": "https://xxx.pptx",
    "templateId": "xxx",
    "pptxProperty": "xxx",
    "userId": "xxx",
    "userName": "xxx",
    "companyId": 1000,
    "updateTime": null,
    "createTime": "2024-01-01 10:00:00"
  }
}
```
> 状态：-1异常 1解析文件 3生成中 4完成

##### 请求示例
```bash
# 非流式
curl -X POST --location 'https://open.docmee.cn/api/ppt/directGeneratePptx' \
--header 'Content-Type: application/json' \
--header 'token: {token}' \
--data '{"stream": false, "subject": "AI未来的发展", "pptxProperty": false}'

# 流式
curl -X POST --location 'https://open.docmee.cn/api/ppt/directGeneratePptx' \
--header 'Content-Type: application/json' \
--header 'token: {token}' \
--data '{"stream": true, "subject": "AI未来的发展", "pptxProperty": false}'
```

### AI PPT (异步)

Ai异步流式生成PPT，只需在调用生成大纲接口后调用下面的generateContent接口即可生成PPT，无需再次调用生成PPT接口。

#### 生成大纲内容同时异步生成PPT

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/generateContent` |
| 请求方法 | POST |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| templateId | string | 否 | 模板ID（非必填） |
| outlineMarkdown | string | 是 | 大纲markdown文本 |
| asyncGenPptx | boolean | 是 | 异步生成PPT（这里必须为true才会流式生成） |
| prompt | string | 否 | 用户要求 |
| dataUrl | string | 否 | 文件数据url，调用解析文件内容接口返回 |

##### 响应
```json
{"text": "", "status": 3, "pptId": "xxx", "total": 23, "current": 1}
{"text": "#", "status": 3}
{"text": " ", "status": 3}
{"text": "主题", "status": 3}
...
{
  "text": "",
  "status": 4,
  "result": {
    "level": 1,
    "name": "主题",
    "children": [
      {
        "level": 2,
        "name": "章节",
        "children": [
          {
            "level": 3,
            "name": "页面标题",
            "children": [
              {
                "level": 4,
                "name": "内容标题",
                "children": [
                  {
                    "level": 0,
                    "name": "内容"
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  }
}
```
> 状态：-1异常 0模型重置 1解析文件 2搜索网页 3生成中 4完成

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/ppt/generateContent' \
--header 'Content-Type: application/json' \
--header 'token: {token}' \
--data '{"outlineMarkdown":"xxx","asyncGenPptx":true}'
```

#### 查询异步生成PPT信息

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/asyncPptInfo?pptId=` |
| 请求方法 | GET |

##### 参数
**pptId** 为generateContent接口流式返回的pptId

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| data.total | number | 总页数 |
| data.current | number | 当前已生成页数（如果current >= total时表示PPT生成完成） |
| data.pptxProperty | string | PPT数据结构（json gzip base64） |
| code | number | 状态码 |

##### 请求示例
```bash
curl -X GET --location 'https://open.docmee.cn/api/ppt/asyncPptInfo?pptId=xxx' \
--header 'token: {token}'
```

> **说明**：该接口不需要轮询，在generateContent接口流式返回pptId数据时调用，每出现一次pptId就调用一次获取最新的PPT信息。
>
> **注意**：这个接口只有在流式生成过程中能查询到数据（临时缓存数据），在PPT生成完成的30秒内过期（查不到数据），此时需要调用loadPptx加载PPT数据接口查询。

### 对话生成PPT

兼容openai chat接口生成PPT，鉴权支持请求头Api-Key和Authorization Bearer两种方式。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt-openai/v1/chat/completions` |
| 请求方法 | POST |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| stream | boolean | 否 | 是否流式 |
| model | string | 是 | 模型（固定：direct-generate-pptx） |
| messages | array | 是 | 消息体：不支持连续对话（多个时默认取最后一个user） |
| appendLink | boolean | 否 | 大纲内容生成完成后是否在文本后面追加封面图片和下载链接（默认true） |
| templateId | string | 否 | 模板ID（默认为null，系统随机） |
| lang | string | 否 | 语言: zh/zh-Hant/en/ja/ko/ar/de/fr/it/pt/es/ru |
| prompt | string | 否 | 用户要求（不超过50字） |

messages结构：
```json
[
  {
    "role": "user",
    "content": "AI未来的发展"
  }
]
```
> 支持：主题、文档内容、文件链接（公网可访问）

##### 非流式响应(application/json)
```json
{
  "id": "1833839690764124160",
  "model": "direct-generate-pptx",
  "choices": [
    {
      "index": 0,
      "finish_reason": "stop",
      "message": {
        "role": "assistant",
        "content": "# AI未来的发展\\n## 1 技术进步\\n### 1.1 算法优化\\n#### 1.1.1 深度学习\\n- 深度学习模型不断优化，提高准确性和效率...|\\n\\n[封面图片]\\n\\n[点击下载]"
      },
      "ppt_data": {
        "id": "1833839690764124160",
        "subject": "AI未来的发展",
        "templateId": "xxx",
        "coverUrl": "https://xxx.png",
        "fileUrl": "https://xxx.pptx"
      }
    }
  ],
  "object": "chat.completion",
  "created": 1726056513,
  "usage": {
    "completion_tokens": 10000,
    "prompt_tokens": 2000,
    "total_tokens": 12000
  }
}
```

##### 流式响应(event-stream)
```text
data: {"id":"1833839690764124160","choices":[{"delta":{"content":"#","role":"assistant"},"finish_reason":null,"index":0}],"created":1726056518,"model":"direct-generate-pptx","object":"chat.completion.chunk"}
data: {"id":"1833839690764124160","choices":[{"delta":{"content":" ","role":"assistant"},"finish_reason":null,"index":0}],"created":1726056518,"model":"direct-generate-pptx","object":"chat.completion.chunk"}
data: {"id":"1833839690764124160","choices":[{"delta":{"content":"AI","role":"assistant"},"finish_reason":null,"index":0}],"created":1726056518,"model":"direct-generate-pptx","object":"chat.completion.chunk"}
...
data: {"id":"1833839690764124160","choices":[{"delta":{"content":null,"role":"assistant"},"finish_reason":"stop","index":0,"ppt_data":{"companyId":1000,"coverUrl":"https://xxx.png","createTime":1726056519624,"fileUrl":"https://xxx.pptx","id":"1833839690764124160","name":"AI未来的发展","subject":"AI未来的发展","templateId":"1815308477845987328","updateTime":1726056519624,"userId":"xxx","userName":"xxx"}}],"created":1726056529,"model":"direct-generate-pptx","object":"chat.completion.chunk"}
```

##### Python请求示例
```python
import json
from openai import OpenAI

if __name__ == '__main__':
    # 通过openai库直接请求
    client = OpenAI(base_url='{域名}/api/ppt-openai/v1', api_key='sk-xxx')
    # 是否流式请求
    stream = True
    response = client.chat.completions.create(
        timeout=120,
        stream=stream,
        model='direct-generate-pptx',
        messages=[
            {
                'role': 'user',
                'content': 'AI未来的发展'
            }
        ]
    )
    if stream:
        # 流式
        for trunk in response:
            choice = trunk['choices'][0]
            print(choice['delta']['content'], end='')
            if 'ppt_data' in choice:
                print(json.dumps(choice['ppt_data']))
    else:
        # 非流式
        choice = response['choices'][0]
        print(choice['message']['content'])
        if 'ppt_data' in choice:
            print(json.dumps(choice['ppt_data']))
```

### MCP

兼容Model Context Protocol(MCP)生成PPT。

| 属性 | 说明 |
|------|------|
| SSE Server端点 | `/api/mcp/sse?token=` |
| 鉴权 | 通过URL上的token参数鉴权，设置为你在平台的Api-Key或通过接口创建的token |

#### tools/list
```json
[
  {
    "name": "ai_generate_ppt",
    "description": "AI generate PPT",
    "inputSchema": {
      "type": "object",
      "properties": {
        "task_description": {
          "type": "string"
        }
      },
      "required": ["task_description"],
      "additionalProperties": false
    }
  }
]
```

#### Typescript接入示例
```typescript
import { Client } from '@modelcontextprotocol/sdk/client/index.js'
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js'

async function main() {
  const apiKey = 'ak_xxx'
  const mcpClient = new Client({
    name: 'mcp-client-test',
    version: '1.0.0',
  })
  const transport = new SSEClientTransport(
    new URL('https://open.docmee.cn/api/mcp/sse?token=' + apiKey),
  )
  mcpClient.connect(transport)
  const toolsResult = await mcpClient.listTools()
  console.log('Tools:', toolsResult)
  const result = await mcpClient.callTool({
    name: 'ai_generate_ppt',
    arguments: {
      task_description: '请以AI未来的发展为主题生成PPT',
    },
  })
  console.log('Result:', result)
}

main()
```

## 模板管理

### 获取模板过滤选项

获取查询模版的过滤选项。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/template/options` |
| 请求方法 | GET |

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| data.category | array | 类目筛选 |
| data.style | array | 风格筛选 |
| data.themeColor | array | 主题颜色筛选 |
| code | number | 状态码 |
| message | string | 提示信息 |

**类目(category)筛选**：
1. {name: "全部", value: ""}
2. {name: "年终总结", value: "年终总结"}
3. {name: "教育培训", value: "教育培训"}
4. {name: "医学医疗", value: "医学医疗"}
5. {name: "商业计划书", value: "商业计划书"}
6. {name: "企业介绍", value: "企业介绍"}
7. {name: "毕业答辩", value: "毕业答辩"}
8. {name: "营销推广", value: "营销推广"}
9. {name: "晚会表彰", value: "晚会表彰"}
10. {name: "个人简历", value: "个人简历"}

**风格(style)筛选**：
1. {name: "全部", value: ""}
2. {name: "扁平简约", value: "扁平简约"}
3. {name: "商务科技", value: "商务科技"}
4. {name: "文艺清新", value: "文艺清新"}
5. {name: "卡通手绘", value: "卡通手绘"}
6. {name: "中国风", value: "中国风"}
7. {name: "创意时尚", value: "创意时尚"}
8. {name: "创意趣味", value: "创意趣味"}

**主题颜色(themeColor)筛选**：
1. {name: "全部", value: ""}
2. {name: "橙色", value: "#FA920A"}
3. {name: "蓝色", value: "#589AFD"}
4. {name: "紫色", value: "#7664FA"}
5. {name: "青色", value: "#65E5EC"}
6. {name: "绿色", value: "#61D328"}
7. {name: "黄色", value: "#F5FD59"}
8. {name: "红色", value: "#E05757"}
9. {name: "棕色", value: "#8F5A0B"}
10. {name: "白色", value: "#FFFFFF"}
11. {name: "黑色", value: "#000000"}

##### 请求示例
```bash
curl -X GET --location 'https://open.docmee.cn/api/ppt/template/options'
```

### 分页查询PPT模板

分页查询PPT模版。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/templates` |
| 请求方法 | POST |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| page | number | 是 | 分页：第几页 |
| size | number | 是 | 分页：每页大小 |
| filters.type | number | 是 | 模板类型（必传）：1系统模板、4用户自定义模板 |
| filters.category | string | 否 | 类目筛选 |
| filters.style | string | 否 | 风格筛选 |
| filters.themeColor | string | 否 | 主题颜色筛选 |

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| code | number | 状态码 |
| total | number | 总数 |
| data[].id | string | 模板ID |
| data[].type | number | 模板类型：1大纲完整PPT、4用户模板 |
| data[].coverUrl | string | 封面（需要拼接?token=${token}访问） |
| data[].category | string/null | 类目 |
| data[].style | string/null | 风格 |
| data[].themeColor | string/null | 主题颜色 |
| data[].subject | string | 主题 |
| data[].num | number | 模板页数 |
| data[].createTime | string | 创建时间 |
| message | string | 提示信息 |

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/ppt/templates' \
--header 'Content-Type: application/json' \
--header 'token: {token}' \
--data '{"page": 1, "size":10, "filters": { "type": 1 }}'
```

> **注意**：
> - 封面图片资源访问，需要在url上拼接`?token=xxx`
> - 模板接口支持国际化，在请求URL上传lang参数，示例：/api/ppt/templates?lang=zh-CN
> - 国际化语种支持：zh,zh-Hant,en,ja,ko,ar,de,fr,it,pt,es,ru

### 随机PPT模板

随机获取若干数量的PPT模版。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/randomTemplates` |
| 请求方法 | POST |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| size | number | 是 | 数量 |
| filters.type | number | 是 | 模板类型（必传）：1系统模板、4用户自定义模板 |
| filters.category | string | 否 | 类目 |
| filters.style | string | 否 | 风格 |
| filters.themeColor | string | 否 | 主题颜色 |
| filters.neq_id | array | 否 | 排查ID集合（把之前查询返回的id排除） |

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| code | number | 状态码 |
| total | number | 总数 |
| data[].id | string | 模板ID |
| data[].type | number | 模板类型：1大纲完整PPT、4用户模板 |
| data[].coverUrl | string | 封面（需要拼接?token=${token}访问） |
| data[].category | string/null | 类目 |
| data[].style | string/null | 风格 |
| data[].themeColor | string/null | 主题颜色 |
| data[].subject | string | 主题 |
| data[].num | number | 模板页数 |
| data[].createTime | string | 创建时间 |
| message | string | 提示信息 |

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/ppt/randomTemplates' \
--header 'Content-Type: application/json' \
--header 'token: {token}' \
--data '{"size":10, "filters": { "type": 1 }}'
```

> **注意**：
> - 封面图片资源访问，需要在url上拼接`?token=xxx`
> - 模板接口支持国际化，在请求URL上传lang参数，示例：/api/ppt/randomTemplates?lang=zh-CN
> - 国际化语种支持：zh,zh-Hant,en,ja,ko,ar,de,fr,it,pt,es,ru

## PPT获取与操作

### 获取PPT列表

分页查询您的PPT作品列表。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/listPptx` |
| 请求方法 | POST |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| page | number | 是 | 分页：第几页 |
| size | number | 是 | 分页：每页大小 |

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| code | number | 状态码 |
| total | number | 总数 |
| data[].id | string | ppt id |
| data[].subject | string | 主题 |
| data[].coverUrl | string | 封面 |
| data[].templateId | string | 模板ID |
| data[].userId | string | 用户ID |
| data[].userName | string | 用户名称 |
| data[].companyId | number | 公司ID |
| data[].updateTime | string/null | 更新时间 |
| data[].createTime | string | 创建时间 |
| message | string | 提示信息 |

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/ppt/listPptx' \
--header 'Content-Type: application/json' \
--header 'token: {token}' \
--data '{"page": 1, "size": 10}'
```

### 加载PPT数据

加载一个PPT的完整数据内容。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/loadPptx?id=` |
| 请求方法 | GET |

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| data.pptInfo.id | string | ppt id |
| data.pptInfo.subject | string | 主题 |
| data.pptInfo.coverUrl | string | 封面 |
| data.pptInfo.templateId | string | 模板ID |
| data.pptInfo.pptxProperty | string | PPT数据结构（json数据通过gzip压缩base64编码返回） |
| data.pptInfo.userId | string | 用户ID |
| data.pptInfo.userName | string | 用户名称 |
| data.pptInfo.companyId | number | 公司ID |
| data.pptInfo.updateTime | string/null | 更新时间 |
| data.pptInfo.createTime | string | 创建时间 |
| code | number | 状态码 |
| message | string | 提示信息 |

##### 请求示例
```bash
curl -X GET --location 'https://open.docmee.cn/api/ppt/loadPptx?id=xxx' \
--header 'token: {token}'
```

### 加载PPT大纲内容

获取生成PPT所使用的大纲内容。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/loadPptxMarkdown` |
| 请求方法 | POST |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| id | string | 是 | pptId |
| format | string | 是 | 输出格式：text大纲文本；tree大纲结构树 |

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| data.markdownText | string | 大纲markdown文本（当format为text时返回） |
| data.markdownTree | object | 大纲结构树（当format为tree时返回） |
| code | number | 状态码 |
| message | string | 提示信息 |

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/ppt/loadPptxMarkdown' \
--header 'Content-Type: application/json' \
--header 'token: {token}' \
--data '{"id": "xxx", "format": "tree"}'
```

### 下载PPT

下载PPT到本地。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/downloadPptx` |
| 请求方法 | POST |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| id | string | 是 | pptId |
| refresh | boolean | 否 | 是否刷新（默认false） |

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| data.id | string | pptId |
| data.name | string | 名称 |
| data.subject | string | 主题 |
| data.fileUrl | string | 文件链接（有效期：2小时） |
| code | number | 状态码 |
| message | string | 提示信息 |

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/ppt/downloadPptx' \
--header 'Content-Type: application/json' \
--header 'token: {token}' \
--data '{"id":"xxx"}'
```

### 下载-智能动画PPT

给PPT自动加上动画再下载到本地。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/downloadWithAnimation?type=1&id=xxx` |
| 请求方法 | GET |

##### URL请求参数
| 参数 | 类型 | 描述 |
|------|------|------|
| type | number | 动画类型，1依次展示（默认）；2单击展示 |
| id | string | PPT ID |

##### 响应
application/octet-stream 文件数据流

##### 请求示例
```bash
curl -X GET --location 'https://open.docmee.cn/api/ppt/downloadWithAnimation?type=1&id=xxx' \
--header 'token: {token}'
```

> **注意**：
> - 该接口会在原有的PPT元素对象上智能添加动画效果（元素入场动画 & 页面切场动画）
> - 动画类型介绍：
>   - 1 依次展示，表示上一个元素动画结束后立马展示下一个元素动画
>   - 2 单击展示，表示在内容页，上一项内容展示完成后需要单击才会展示下一项内容，其他页面效果同依次展示。

### 更换PPT模板

更换PPT的模板。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/updatePptTemplate` |
| 请求方法 | POST |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| pptId | string | 是 | ppt id |
| templateId | string | 是 | 模板ID |
| sync | boolean | 否 | 是否同步更新PPT文件（默认false异步更新，速度快） |

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| data.pptId | string | pptId |
| data.templateId | string | 模板ID |
| data.pptxProperty | object | 更换后的pptx结构数据（json） |
| code | number | 状态码 |

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/ppt/updatePptTemplate' \
--header 'Content-Type: application/json' \
--header 'token: {token}' \
--data '{"pptId":"xxx","templateId":"xxx","sync":false}'
```

### 更新PPT属性

修改PPT的名称或主题。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/updatePptxAttr` |
| 请求方法 | POST |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| id | string | 是 | ppt id |
| name | string | 否 | 名称（不能为空则修改） |
| subject | string | 否 | 主题（不能为空则修改） |

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| code | number | 状态码 |
| message | string | 提示信息 |

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/ppt/updatePptxAttr' \
--header 'Content-Type: application/json' \
--header 'token: {token}' \
--data '{"id":"xxx","name":"xxx"}'
```

### 设置Logo

设置PPT的LOGO。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/addPptLogo` |
| 请求方法 | POST |
| Content-Type | `multipart/form-data` |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| pptId | string | 是 | PPT ID |
| image | File | 是 | Logo图片文件（png / jpg） |
| position | string | 是 | Logo位置：`TOP_LEFT`、`TOP_CENTER`、`TOP_RIGHT`、`BOTTOM_LEFT`、`BOTTOM_CENTER`、`BOTTOM_RIGHT` |
| pageIndex | integer | 否 | 指定页码（从1开始） |
| pageTypes | number[] | 否 | 指定页面类型数组 |
| marginX | number | 否 | X方向边距 |
| marginY | number | 否 | Y方向边距 |
| scale | number | 是 | Logo缩放比例 |
| rmOrgLogo | boolean | 是 | 是否移除原有Logo |

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| data.fileUrl | string | pptx文件下载地址 |
| code | number | 状态码 |
| message | string | 提示信息 |

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/ppt/addPptLogo' \
--header 'Content-Type: multipart/form-data' \
--header 'token: {token}' \
--form 'pptId=12354768' \
--form 'image=@test.png;filename=test.png' \
--form 'position=TOP_RIGHT' \
--form 'scale=1' \
--form 'rmOrgLogo=true' \
--form 'marginX=0' \
--form 'marginY=0'
```

### 移除Logo

移除PPT的LOGO。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/removePptLogo` |
| 请求方法 | POST |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| pptId | string | 是 | PPT ID |
| pageIndex | integer | 否 | 指定页码（从1开始） |
| pageTypes | number[] | 否 | 指定页面类型数组 0:首页, 1:目录页, 2:章节页, 3:内容页, 4:尾页 |

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| code | number | 状态码 |
| message | string | 提示信息 |

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/ppt/removePptLogo' \
--header 'Content-Type: application/json' \
--header 'token: {token}' \
--data '{"pptId":"12354768","pageIndex":1,"pageTypes":[1,2]}'
```

### 保存PPT

保存PPT的修改。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/savePptx` |
| 请求方法 | POST |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| id | string | 是 | ppt id |
| drawPptx | boolean | 否 | 是否重新渲染PPT文件并上传 |
| drawCover | boolean | 否 | 是否重新渲染PPT封面并上传 |
| pptxProperty | object | 否 | 修改过后的pptx页面数据结构树 |

> 如果您只想要重新渲染ppt，您可以传递drawPptx为true。这时您可以传递最新的pptxProperty结构来渲染，如果您没有最新的pptxProperty结构，该字段请不要传递，留空即可。

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| data.pptInfo | object | ppt信息（数据同generatePptx生成PPT接口结构） |
| code | number | 状态码 |
| message | string | 提示信息 |

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/ppt/savePptx' \
--header 'Content-Type: application/json' \
--header 'token: {token}' \
--data '{"id":"xxx","drawPptx":true,"drawCover":true,"pptxProperty":{}}'
```

### 删除PPT

删除指定的PPT。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/delete` |
| 请求方法 | POST |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| id | string | 是 | ppt id |

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| code | number | 状态码 |
| message | string | 提示信息 |

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/ppt/delete' \
--header 'Content-Type: application/json' \
--header 'token: {token}' \
--data '{"id":"xxx"}'
```

## 自定义模板

### 上传用户自定义模板

上传用户自定义的PPT模板。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/uploadTemplate` |
| 请求方法 | POST |
| Content-Type | `multipart/form-data` |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| type | int | 是 | 类型，用户自定义模板传4（写死） |
| file | File | 是 | 文件（仅支持pptx，幻灯片大小960x540） |
| templateId | string | 否 | 模板ID（更新时传，会覆盖该模板） |

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| data.id | string | 模板ID |
| data.type | number | 模板类型：4用户模板 |
| data.coverUrl | string | 封面（需要拼接token才能访问） |
| data.subject | string | 主题 |
| data.pptxProperty | string | PPT数据结构（json gzip base64） |
| data.num | number | 页码 |
| data.createTime | string | 创建时间 |
| code | number | 状态码 |
| message | string | 提示信息 |

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/ppt/uploadTemplate' \
--header 'Content-Type: multipart/form-data' \
--header 'token: {token}' \
--form 'type=4' \
--form 'file=@test.doc;filename=test.doc'
```

> **注意**：
> - 模板标准幻灯片大小（16:9）960x540 (33.867x19.05厘米)，如果尺寸非标准大小，可在microsoft office中修改步骤：设计 > 幻灯片大小 > 自定义幻灯片大小 => 33.867x19.05厘米
> - 上传用户自定义模板后，AI会自动标注学习，如果您觉得生成效果有问题，对不上，可以访问下面链接手动纠正AI标注结果：[https://docmee.cn/marker/{templateId}?token={apiKey}](https://docmee.cn/marker/%5C%7BtemplateId%5C%7D?token=%5C%7BapiKey%5C%7D) 请把{templateId}替换成真实的模板ID，{apiKey}替换成你的api-key，示例：<https://docmee.cn/marker/10000?token=xxx>
> - 注意：如果是覆盖公共模板，请把token换成Api-Key调用，不然无权限访问。

### 下载自定义模板

下载用户自定义的模板。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/downloadTemplate` |
| 请求方法 | POST |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| id | string | 是 | 模板ID |

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| data.id | string | 模板ID |
| data.subject | string | 主题 |
| data.type | number | 模板类型：4用户模板 |
| data.coverUrl | string | 封面（需要拼接token才能访问） |
| data.fileUrl | string | 模板下载地址（可直接访问） |
| data.createTime | string | 创建时间 |
| code | number | 状态码 |
| message | string | 提示信息 |

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/ppt/downloadTemplate' \
--header 'Content-Type: application/json' \
--header 'token: {token}' \
--data '{"id": "xxx"}'
```

### 删除自定义模板

删除用户自定义的模板。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/delTemplateId` |
| 请求方法 | POST |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| id | string | 是 | 模板ID |

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| code | number | 状态码 |
| message | string | 提示信息 |

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/ppt/delTemplateId' \
--header 'Content-Type: application/json' \
--header 'token: {token}' \
--data '{"id": "xxx"}'
```

### 修改模版属性（名称）

修改自定义模版的信息（名称）。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/updateTemplate` |
| 请求方法 | POST |

##### 请求头
| 头部 | 说明 |
|------|------|
| Api-Key | 在开放平台获取 |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| id | string | 是 | 模板Id |
| name | string | 是 | 模板名称 |

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| code | number | 状态码 |
| message | string | 提示信息 |

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/ppt/updateTemplate' \
--header 'Content-Type: application/json' \
--header 'Api-Key: {apiKey}' \
--data '{"id": "xxx", "name": "测试修改111"}'
```

### 设置为公共模板

将自定义模版设置为Api-Key账号级别的公共模板，但并非平台公共模板。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/updateUserTemplate` |
| 请求方法 | POST |

##### 请求头
| 头部 | 说明 |
|------|------|
| Api-Key | 在开放平台获取 |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| templateId | string | 是 | 模板ID |
| isPublic | boolean | 是 | 是否公开（true公开，API-KEY下创建的所有token可以看到） |

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| code | number | 状态码 |
| message | string | 提示信息 |

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/ppt/updateUserTemplate' \
--header 'Content-Type: application/json' \
--header 'Api-Key: {apiKey}' \
--data '{"templateId": "xxx", "isPublic": true}'
```

## 积分和使用记录

### 查询API信息

获取当前用户的积分使用情况。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/user/apiInfo` |
| 请求方法 | GET |

##### 请求头
| 头部 | 说明 |
|------|------|
| Api-Key | 在开放平台获取 |

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| data.availableCount | number | 可用次数 |
| data.usedCount | number | 已使用次数 |
| code | number | 状态码 |
| message | string | 提示信息 |

##### 请求示例
```bash
curl -X GET --location 'https://open.docmee.cn/api/user/apiInfo' \
--header 'Api-Key: xxx'
```

### 查询积分使用记录

获取一段时间内的积分使用记录。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/record/listPage` |
| 请求方法 | POST |

##### 请求头
| 头部 | 说明 |
|------|------|
| Api-Key | 在开放平台获取 |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| page | number | 是 | 分页：第几页 |
| size | number | 是 | 分页：每页大小 |
| type | number | 否 | 类型：1 PPT生成；2 模板上传；（默认全部） |
| uid | string | 否 | 第三方用户ID |
| startDate | string | 是 | 查询开始时间（必须） |
| endDate | string | 是 | 查询结束时间（必须） |

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| total | number | 总数 |
| data[].id | string | 记录ID（ppt ID或模板ID） |
| data[].type | number | 记录类型：1 ppt生成; 2 模板上传 |
| data[].amount | number | 消耗积分 |
| data[].uid | string | 第三方用户ID |
| data[].createTime | string | 创建时间 |
| code | number | 状态码 |
| message | string | 提示信息 |

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/record/listPage' \
--header 'Content-Type: application/json' \
--header 'Api-Key: xxx' \
--data '{ "page": 1, "size": 100, "type": 1, "startDate": "2025-01-01", "endDate": "2025-12-31" }'
```

### 查询记录详情

获取一条积分使用记录的详细信息。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/record/getById?id=` |
| 请求方法 | GET |

##### 参数
id参数: 记录ID

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| data.id | string | PPT Id或模板ID |
| data.name | string | 名称 |
| data.subject | string | 主题 |
| data.coverUrl | string | 封面图（需在URL拼接token才能访问） |
| data.fileUrl | string | pptx文件（需在URL拼接token才能访问） |
| data.templateId | string | type=1的PPT记录才有templateId字段 |
| data.userId | string | 用户ID |
| data.userName | string | 用户名称 |
| data.updateTime | string | 修改时间 |
| data.createTime | string | 创建时间 |
| code | number | 状态码 |
| message | string | 提示信息 |

##### 请求示例
```bash
curl -X GET --location 'https://open.docmee.cn/api/record/getById?id=xxx' \
--header 'Api-Key: xxx'
```

### 按小时统计积分使用

按小时统计积分使用情况。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/record/statisticHours` |
| 请求方法 | POST |

##### 请求头
| 头部 | 说明 |
|------|------|
| Api-Key | 在开放平台获取 |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| type | number | 否 | 类型：1 生成PPT；2 上传模板；默认全部 |
| uid | string | 否 | 第三方用户ID |
| date | string | 是 | 日期（必须） |

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| data[].count | number | 使用次数 |
| data[].hour | number | 时间-小时整点(0-24) |
| data[].amount | number | 消耗积分数 |
| code | number | 状态码 |
| message | string | 提示信息 |

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/record/statisticHours' \
--header 'Content-Type: application/json' \
--header 'Api-Key: xxx' \
--data '{ "type": 1, "date": "2025-01-01" }'
```

### 按天统计积分使用

按天统计积分使用情况。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/record/statisticDays` |
| 请求方法 | POST |

##### 请求头
| 头部 | 说明 |
|------|------|
| Api-Key | 在开放平台获取 |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| type | number | 否 | 类型：1 生成PPT；2 上传模板；默认全部 |
| uid | string | 否 | 第三方用户ID |
| startDate | string | 是 | 查询开始时间（必须） |
| endDate | string | 是 | 查询结束时间（必须） |

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| data[].count | number | 使用次数 |
| data[].date | string | 日期 |
| data[].amount | number | 消耗积分 |
| code | number | 状态码 |
| message | string | 提示信息 |

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/record/statisticDays' \
--header 'Content-Type: application/json' \
--header 'Api-Key: xxx' \
--data '{ "type": 1, "startDate": "2025-01-01", "endDate": "2025-12-31" }'
```

### 查询所有PPT列表

获取当前Api-Key下一段时间内所有生成的PPT文件。

| 属性 | 说明 |
|------|------|
| 接口地址 | `https://open.docmee.cn/api/ppt/listAllPptx` |
| 请求方法 | POST |

##### 请求头
| 头部 | 说明 |
|------|------|
| Api-Key | 在开放平台获取 |

##### 请求参数
| 参数 | 类型 | 是否必传 | 说明 |
|------|------|----------|------|
| page | number | 是 | 分页 |
| size | number | 是 | 每页大小（最大不超过100） |
| id | string | 否 | ppt id（非必填） |
| uid | string | 否 | 第三方用户ID（非必填） |
| templateId | string | 否 | 模板ID（非必填） |
| startDate | string | 否 | 创建开始时间（非必填） |
| endDate | string | 否 | 创建结束时间（非必填） |
| desc | boolean | 否 | 按时间倒序返回（非必填） |

##### 响应参数
| 参数 | 类型 | 说明 |
|------|------|------|
| code | number | 状态码 |
| total | number | 总数 |
| data[].id | string | ppt id |
| data[].subject | string | 主题 |
| data[].coverUrl | string | 封面（需要拼接?token={API-KEY}访问） |
| data[].fileUrl | string | 文件（需要拼接?token={API-KEY}访问） |
| data[].templateId | string | 模板ID |
| data[].userId | string | 用户ID / uid |
| data[].companyId | number | 公司ID |
| data[].createTime | string | 创建时间 |
| message | string | 提示信息 |

##### 请求示例
```bash
curl -X POST --location 'https://open.docmee.cn/api/ppt/listAllPptx' \
--header 'Content-Type: application/json' \
--header 'Api-Key: xxx' \
--data '{"page": 1, "size": 10}'
```

## 错误码

### 接口application/json错误
```json
{
  "code": 0,
  "message": "操作成功"
}
```

| 错误码 | 说明 |
|-------|------|
| 0 | 操作成功（正常） |
| -1 | 操作失败（未知错误） |
| 88 | 功能受限（积分已用完或非VIP） |
| 98 | 认证失败（检查token是否过期） |
| 99 | 登录过期 |
| 1001 | 数据不存在 |
| 1002 | 数据访问异常 |
| 1003 | 无权限访问 |
| 1006 | 内容涉及敏感信息 |
| 1009 | AI服务异常 |
| 1010 | 参数错误 |
| 1012 | 请求太频繁，限流 |

### SEE流式请求错误

初始化流式调用时发生错误会返回application/json错误信息：
```json
{
  "code": 1010,
  "message": "参数错误：name不能为空"
}
```

流式过程中遇到错误，会在流中返回text/event-stream流式错误信息：
```text
data: {"status":-1, "error":"AI模型执行异常"}
```

## 特殊说明

### PPT前端渲染

关于ppt数据结构在前端渲染问题，我们已经把前端代码开源到github：

- <https://github.com/docmee/aippt-js>
- <https://github.com/docmee/aippt-vue-all>
- <https://github.com/docmee/aippt-react>

### Markdown规范

适用于调用方需要通过自己内容和模型生成PPT内容，调用方根据我们的规范生成markdown内容，然后调用接口合成PPT。

#### 规范示例
```markdown
# 主题

## 章节

### 页面标题

#### 内容标题一

这是文本内容...
![图片一](https://xxx.png)

#### 内容标题二

这是文本内容...
![图片二](https://xxx.png)
```

#### 规范说明
- `# 主题`（一级标题，必须包含，只能有一个）
- `## 章节一`（二级标题，目录章节，必须包含，建议6个章节左右）
- `### 页面一`（三级标题，页面标题，每个章节下建议3个左右，30字以内）
- `#### 段落标题一`（四级标题，段落标题，每个页面下建议3个左右，30字以内）
- `- 段落文本内容`（内容长度建议在40-80字之间）

表格支持：
```markdown
| 季度     | 销售额 |
| -------- | ------ |
| 第一季度 | 380.0  |
| 第二季度 | 826.5  |
| 第三季度 | 512.2  |
| 第四季度 | 674.0  |
```

> markdown规范没有定这么死，除了主题（一级标题）和章节（二级标题）必须包含外，其他标题可以没有。

完整markdown示例下载：[markdown.md](https://metasign-public.oss-cn-shanghai.aliyuncs.com/docmee/markdown.md)

生成markdown后，调用generatePptx生成PPT接口，对应outlineContentMarkdown参数。

### 接入示例

官方提供了多种语言的接入示例：

- UI接入示例V2: <https://github.com/docmee/aippt-ui-iframe-v2>
- UI接入示例V1: <https://github.com/docmee/aippt-ui-iframe>
- Python Api接入示例: <https://github.com/docmee/aippt-api-python-demo>
- Java Api接入示例: <https://github.com/docmee/aippt-api-java-demo>
- Go Api接入示例: <https://github.com/docmee/aippt-api-go-demo>
- PHP Api接入示例: <https://github.com/docmee/aippt-api-php-demo>

### PPT生成方式说明

官方最推荐使用**版本2**来创作PPT，也是官方应用[文多多AiPPT](https://docmee.cn)中使用的方式。

#### 版本2(官方推荐)
1. 调用`createTask`创建任务
2. 调用`generateContent`生成大纲内容
3. 调用`generatePptx`生成PPT

#### 直接生成PPT
- 调用`directGeneratePptx`直接生成PPT接口，支持流式和非流式

#### 实时流式生成PPT(版本1)
1. 调用`generateOutline`生成大纲
2. 调用`generateContent`生成大纲内容同时异步生成PPT
3. 在第二步中接收实时流式json数据过程中判断是否有pptId，存在时调用`asyncPptInfo`获取进度

#### 同步流式生成PPT(版本1)
1. 调用`generateOutline`生成大纲
2. 调用`generateContent`生成大纲内容
3. 调用`generatePptx`生成PPT

#### openai chat方式生成PPT
- 调用`/chat/completions`OpenAi-对话生成PPT接口

#### 通过markdown生成PPT
- 集成方生成markdown内容，然后调用`generatePptx`生成PPT

#### MCP
- 兼容Model Context Protocol(MCP)生成PPT