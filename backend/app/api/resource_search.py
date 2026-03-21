"""教学资源搜索：转发 Dify「资源推荐助手」工作流。"""
import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, status

from app.core.auth import CurrentUser
from app.schemas.resource_search import (
    ResourceItem,
    ResourceSearchRequest,
    ResourceSearchResponse,
)
from app.services.dify_resource_recommend import (
    build_resource_workflow_inputs,
    run_resource_recommend_workflow,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resource-search", tags=["resource-search"])


@router.post("/recommend", response_model=ResourceSearchResponse)
async def recommend_resources(payload: ResourceSearchRequest, user: CurrentUser):
    """
    根据关键词与筛选条件调用 Dify 工作流，返回卡片化资源列表。
    需在环境变量中配置 DIFY_RESOURCE_WORKFLOW_API_KEY（Dify 应用 API Key）。
    """
    if not (payload.keyword or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请输入搜索关键词",
        )

    inputs = build_resource_workflow_inputs(
        keyword=payload.keyword,
        grade=payload.grade,
        subject=payload.subject,
        file_type=payload.file_type,
        sort_by=payload.sort_by,
    )
    if not (inputs["node_name"] or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="搜索条件无效，请检查关键词或筛选项",
        )

    dify_user = f"teacher-{user.id}"

    try:
        raw_items, raw_text, wf_id = await run_resource_recommend_workflow(
            course_name=inputs["course_name"],
            node_name=inputs["node_name"],
            dify_user=dify_user,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except RuntimeError as e:
        logger.exception("Dify resource recommend failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception("Unexpected error in resource recommend")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"资源推荐服务异常: {e!s}",
        ) from e

    items = [ResourceItem(**x) for x in raw_items]
    raw_preview = (raw_text or "")[:4000] if raw_text else None

    return ResourceSearchResponse(
        items=items,
        raw_output=raw_preview,
        workflow_run_id=wf_id,
    )
