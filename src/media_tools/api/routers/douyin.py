from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/douyin", tags=["douyin"])

try:
    from f2.apps.douyin.handler import DouyinHandler
    from f2.apps.douyin.utils import SecUserIdFetcher
except Exception:
    DouyinHandler = None
    SecUserIdFetcher = None


@router.get("/metadata")
async def get_metadata(url: str, max_counts: int = 10):
    try:
        from media_tools.douyin.core.f2_helper import get_f2_kwargs

        if DouyinHandler is None or SecUserIdFetcher is None:
            raise HTTPException(status_code=500, detail="f2 not installed")

        sec_user_id = await SecUserIdFetcher.get_sec_user_id(url)
        if not sec_user_id:
            raise HTTPException(status_code=400, detail="Invalid URL or unable to parse sec_user_id")

        kwargs = get_f2_kwargs()
        kwargs["url"] = url
        kwargs["timeout"] = min(int(kwargs.get("timeout") or 20), 10)

        handler = DouyinHandler(kwargs)
        user_profile = await handler.fetch_user_profile(sec_user_id)
        if not user_profile:
            raise HTTPException(status_code=404, detail="User profile not found")

        videos = []
        async for page in handler.fetch_user_post_videos(sec_user_id, max_counts=max_counts):
            if hasattr(page, "_to_list"):
                page_data = page._to_list()
                for video in page_data[:max_counts]:
                    aweme_id = str(video.get("aweme_id") or "")
                    cover_url = (
                        video.get("video", {}).get("cover", {}).get("url_list", [None])[0]
                        or video.get("cover")
                        or ""
                    )
                    videos.append(
                        {
                            "aweme_id": aweme_id,
                            "desc": video.get("desc", ""),
                            "create_time": video.get("create_time", 0),
                            "video_url": f"https://www.douyin.com/video/{aweme_id}",
                            "cover_url": cover_url,
                        }
                    )
                    if len(videos) >= max_counts:
                        break
            else:
                aweme_id = str(getattr(page, "aweme_id", "") or "")
                cover_url = ""
                cover = getattr(page, "video_play_addr", None)
                if isinstance(cover, dict):
                    cover_url = str(cover.get("cover") or "")
                videos.append(
                    {
                        "aweme_id": aweme_id,
                        "desc": getattr(page, "desc", "") or "",
                        "create_time": getattr(page, "create_time", 0) or 0,
                        "video_url": f"https://www.douyin.com/video/{aweme_id}",
                        "cover_url": cover_url,
                    }
                )
            break

        return {
            "creator": {
                "uid": getattr(user_profile, "uid", sec_user_id),
                "nickname": getattr(user_profile, "nickname", sec_user_id),
                "avatar": getattr(user_profile, "avatar_larger", ""),
            },
            "videos": videos[:max_counts]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
