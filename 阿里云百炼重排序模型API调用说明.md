# 阿里云百炼重排序模型API调用说明

## 一、模型概述

重排序模型用于对检索召回的文档进行二次精准排序，将与用户查询最相关的结果排在前列，有效提升检索类应用的准确率。阿里云百炼目前支持三款重排序模型，核心参数与计费信息如下表所示：

|模型名称|最大Document数量|单条最大输入Token|请求最大输入Token|语种支持|单价（每千Token）|免费额度|核心应用场景|
|---|---|---|---|---|---|---|---|
|qwen3-vl-rerank|100|8000|800000|中、英、日、韩、法、德等33种主流语言|图片：0.0018元<br>文字：0.0007元|100万Token（百炼开通后90天内）|图像聚类、跨模态搜索、图片检索|
|qwen3-rerank|500|4000|120000|中、英、西、法等100+主流语种|0.0005元|100万Token（百炼开通后90天内）|文本语义检索、RAG应用|
|gte-rerank-v2|30000|-|-|中、英、日、韩、阿语等50余语种|0.0008元|100万Token（百炼开通后90天内）|大规模文本排序、多语种检索|
### 关键参数说明

1. **单条最大输入Token**：单个Query（查询语句）或Document（文档）的最大Token数，超长会被截断，可能导致排序结果不准确。

2. **最大Document数量**：单次API请求中可传入的文档数量上限。

3. **请求最大输入Token**：计算公式为 `Query Tokens × Document 数量+ Document Tokens 总和`，请求值不得超过该上限。

### 输入格式限制

仅`qwen3-vl-rerank`支持图片、视频类型输入，格式要求如下：

- 图片：JPEG、PNG、WEBP、BMP、TIFF、ICO、DIB、ICNS、SGI（支持URL/Base64）

- 视频：MP4、AVI、MOV（仅支持URL）

## 二、前提条件

1. 已开通阿里云百炼服务，并获取**API Key**（DASHSCOPE_API_KEY）。
2. 若通过SDK调用，需提前安装阿里云百炼DashScope SDK。
4. RAM子账号调用需授予`AliyunBailianDataFullAccess`策略权限，主账号默认拥有全权限。

## 三、HTTP接口调用

### 1. 通用接口信息

#### 接口地址

- 标准接口：`POST https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank`

#### 请求头（Headers）

所有请求均需携带以下必选请求头：

|参数名|类型|必填|值示例|说明|
|---|---|---|---|---|
|Content-Type|string|是|application/json|请求内容类型，固定值|
|Authorization|string|是|Bearer sk-xxxxxx|身份认证，格式为`Bearer + 空格 + API Key`|
#### 通用请求体参数

|参数名|类型|必填|说明|
|---|---|---|---|
|model|string|是|模型名称，可选：qwen3-rerank/qwen3-vl-rerank/gte-rerank-v2|
|input|object|是|输入内容，包含query（查询）和documents（文档列表），当使用 `qwen3-rerank` 模型时，无需使用 `input` 对象参数。此时，`query` 和 documents 参数需与 `model` 等参数位于同一层级。|
|**query**|string|是|查询文本|
|**documents**|*array*|是|待排序的候选文档列表。每个元素是一个字符串。<br/>当使用qwen3-vl-embedding模型时，每个元素是一个字典或者字符串，用于指定内容的类型和值。格式为{"模态类型": "输入字符串或图像、视频url"}。支持text, image, video三种模态类型。<br/>文本：key为text。value为字符串形式。也可不通过dict直接传入字符串。<br/>图片：key为image。value可以是公开可访问的URL，或Base64编码的Data URI。Base64格式为 data:image/{format};base64,{data}，其中 {format} 是图片格式（如 jpeg、png），{data} 是Base64编码字符串。<br/>视频：key为video，value必须是公开可访问的URL。|
|parameters|object|否|扩展参数，如top_n（返回前N条）、return_documents（是否返回原文档）|
### 2. 各模型调用示例

#### （1）qwen3-rerank（文本重排序）

```Bash

curl --request POST \
 --url https://dashscope.aliyuncs.com/compatible-api/v1/reranks \
 --header "Authorization: Bearer $DASHSCOPE_API_KEY" \
 --header "Content-Type: application/json" \
 --data '{
 "model": "qwen3-rerank",
 "documents": [
 "文本排序模型广泛用于搜索引擎和推荐系统中，它们根据文本相关性对候选文本进行排序",
 "量子计算是计算科学的一个前沿领域",
 "预训练语言模型的发展给文本排序模型带来了新的进展"
 ],
 "query": "什么是文本排序模型",
 "top_n": 2,
 "instruct": "Given a web search query, retrieve relevant passages that answer the query."
}'
```

#### （2）qwen3-vl-rerank（跨模态重排序）

支持文本、图片、视频混合输入：

```Bash

curl --location 'https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank' \
--header "Authorization: Bearer $DASHSCOPE_API_KEY" \
--header 'Content-Type: application/json' \
--data '{
 "model": "qwen3-vl-rerank",
 "input":{
 "query": "什么是文本排序模型",
 "documents": [
 {"text": "文本排序模型广泛用于搜索引擎和推荐系统中，它们根据文本相关性对候选文本进行排序"},
 {"image": "https://img.alicdn.com/imgextra/i3/O1CN01rdstgY1uiZWt8gqSL_!!6000000006071-0-tps-1970-356.jpg"},
 {"video": "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20250107/lbcemt/new+video.mp4"}
 ]
 },
 "parameters": {
 "return_documents": true,
 "top_n": 2,
 "fps": 1.0
 }
}'
```

#### （3）gte-rerank-v2（大规模文本重排序）

```Bash

curl --location 'https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank' \
--header "Authorization: Bearer $DASHSCOPE_API_KEY" \
--header 'Content-Type: application/json' \
--data '{
 "model": "gte-rerank-v2",
 "input":{
 "query": "什么是文本排序模型",
 "documents": [
 "文本排序模型广泛用于搜索引擎和推荐系统中，它们根据文本相关性对候选文本进行排序",
 "量子计算是计算科学的一个前沿领域",
 "预训练语言模型的发展给文本排序模型带来了新的进展"
 ]
 },
 "parameters": {
 "return_documents": true,
 "top_n": 2
 }
}'
```

### 3. 通用响应参数

请求体为JSON格式，包含模型指定、输入内容、扩展参数三大核心部分，通用参数如下，各模型特殊适配说明见后续调用示例：

#### （1）成功响应参数

API调用成功后，将返回JSON格式响应，包含请求状态、排序结果、相关元信息；调用失败将返回错误码及错误描述，具体说明如下：

#### （2）失败响应参数

| 参数名                 | 类型    | 必返                                                      | 说明                                                  | 示例值                  |
| ---------------------- | ------- | --------------------------------------------------------- | ----------------------------------------------------- | ----------------------- |
| request_id             | string  | 是                                                        | 请求唯一标识，用于排查调用异常、追溯请求记录          | req-xxxxxx123456        |
| code                   | integer | 是                                                        | 响应状态码，200表示调用成功，非200表示调用失败        | 200                     |
| message                | string  | 是                                                        | 响应信息，成功时返回"success"，失败时返回具体错误描述 | success                 |
| output                 | object  | 是                                                        | 包含重排序后的结果列表及相关信息                      | {results: []}           |
| output.results         | array   | 是                                                        | 排序后的结果列表，按与query的相似度降序排列           | [{index:0, score:0.92}] |
| output.results[].index | integer | 是                                                        | 对应输入documents列表中的索引，用于关联原文档         | 0                       |
| output.results[].score | float   | 是                                                        | 相似度分数，范围0-1，分数越高表示与query相关性越强    | 0.92                    |
| usage                  | object  | 是                                                        | 调用消耗的Token信息，用于计费统计                     | {total_tokens: 120}     |
| 参数名                 | 类型    | 说明                                                      | 示例                                                  |                         |
| ---                    | ---     | ---                                                       | ---                                                   |                         |
| request_id             | string  | 请求唯一标识，用于阿里云技术支持排查问题                  | req-xxxxxx123456                                      |                         |
| code                   | integer | 错误状态码，不同码值对应不同错误类型（如401表示认证失败） | 401                                                   |                         |
| message                | string  | 错误详细描述，明确告知失败原因（如API Key无效）           | Invalid API Key                                       |                         |

#### （3）常见错误码说明

当调用失败时（code≠200），响应将返回错误详情，用于定位问题，格式如下：

| 错误码                                     | 错误描述（示例）                                            | 解决方案                                                     |
| ------------------------------------------ | ----------------------------------------------------------- | ------------------------------------------------------------ |
| 401                                        | Invalid API Key / Authorization header is missing           | 检查API Key是否正确，确认Authorization请求头格式为「Bearer + 空格 + API Key」 |
| 400                                        | documents count exceeds maximum limit / token exceeds limit | 减少documents列表数量（不超过对应模型上限），或截断超长的query/文档 |
| 404                                        | Model not found / API endpoint not found                    | 检查model参数是否正确，确认接口地址与模型匹配（兼容接口仅支持qwen3-rerank） |
| 500                                        | Internal server error                                       | 稍作重试，若多次失败，携带request_id联系阿里云百炼技术支持   |
| 汇总高频调用错误，便于快速定位并解决问题： |                                                             |                                                              |

####

## 四、知识库Retrieve API中重排序配置

在阿里云百炼知识库检索接口（Retrieve API）中，可直接配置重排序参数，实现**检索+重排序**一体化调用，核心配置如下：

### 1. 核心重排序参数

|参数名|类型|必填|取值范围|默认值|说明|
|---|---|---|---|---|---|
|EnableReranking|boolean|否|true/false|true|是否开启重排序|
|Rerank.ModelName|string|否|qwen3-rerank/qwen3-rerank-hybrid/gte-rerank/gte-rerank-hybrid|空|指定重排序模型，覆盖知识库默认配置；推荐使用qwen3-rerank（纯语义）/qwen3-rerank-hybrid（语义+文本匹配）|
|Rerank.RerankMinScore|float|否|0.01-1.00|知识库默认值|相似度阈值，仅返回分数超过该值的文档|
|Rerank.RerankTopN|integer|否|1-20|5|重排序后返回的前N条结果|