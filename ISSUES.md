

# 现在需要完善RAG系统的后端部分，要求如下：

1. 检索加上rerank重排序模型

对接阿里云百炼平台的qwen3-vl-rerank模型，APIkey为sk-98db5cc157b344db851b93ac7780dcd9

API接口文档说明在 阿里云百炼重排序模型API调用说明.md 中，对接接口时有不清楚的内容可以查询此文档

API代码示例为

```curl
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
