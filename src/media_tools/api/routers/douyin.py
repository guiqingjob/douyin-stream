from fastapi import APIRouter, HTTPException
import asyncio
from f2.apps.douyin.handler import DouyinHandler
from f2.apps.douyin.utils import SecUserIdFetcher

router = APIRouter(prefix="/api/v1/douyin", tags=["douyin"])

@router.get("/metadata")
async def get_metadata(url: str, max_counts: int = 10):
    try:
        sec_user_id = await SecUserIdFetcher.get_sec_user_id(url)
        if not sec_user_id:
            raise HTTPException(status_code=400, detail="Invalid URL or unable to parse sec_user_id")

        handler = DouyinHandler({"cookie": ""}) # Basic init
        user_profile = await handler.fetch_user_profile(sec_user_id)
        if not user_profile:
            raise HTTPException(status_code=404, detail="User profile not found")

        videos = []
        async for aweme in handler.fetch_user_post_videos(sec_user_id, max_counts=max_counts):
            videos.append({
                "aweme_id": aweme.aweme_id,
                "desc": aweme.desc,
                "create_time": aweme.create_time,
                "video_url": f"https://www.douyin.com/video/{aweme.aweme_id}",
                "cover_url": aweme.video_play_addr.get('cover', '') if hasattr(aweme, 'video_play_addr') else ''
            })

        return {
            "creator": {
                "uid": sec_user_id,
                "nickname": user_profile.nickname,
                "avatar": user_profile.avatar_larger
            },
            "videos": videos
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
