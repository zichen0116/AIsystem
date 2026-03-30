"""
文件上传路由
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, status
from app.core.auth import CurrentUser
from app.services import oss_service

router = APIRouter(prefix="/upload", tags=["文件上传"])


@router.post("")
async def upload_file(
    current_user: CurrentUser,
    file: UploadFile = File(...),
):
    """
    上传文件到 OSS。

    - 鉴权：必须登录
    - 限制：≤50MB，MIME 白名单
    - 返回：{ url, file_name, file_type }
    """
    try:
        result = await oss_service.upload_file(file, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return result
