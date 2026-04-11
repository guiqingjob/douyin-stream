"""文本处理工具"""
from __future__ import annotations


def clean_video_title(raw_title: str) -> str:
    """清洗视频标题：去掉换行符和 #话题标签，并智能截断长标题"""
    # 1. 按换行分割，取第一行（正文）
    main_part = raw_title.replace('<br>', '\n').split('\n')[0]

    # 2. 截取第一个 # 之前的内容
    if '#' in main_part:
        clean = main_part[:main_part.index('#')].strip()
    else:
        clean = main_part.strip()

    # 3. 智能截断：限制到 40 字以内，保持核心语义
    if len(clean) > 40:
        # 优先在句末标点（？ ！ 。）截断
        for p in ['？', '！', '。']:
            idx = clean.find(p)
            if 10 < idx < 50:
                return clean[:idx + 1].strip()

        # 其次在空格处截断（适合长标题中的短语）
        space_idx = clean.find(' ')
        if space_idx > 15:
            return clean[:space_idx].strip()

        # 再次在逗号处截断（适合长句子）
        comma_idx = clean.find('，')
        if comma_idx > 10:
            return clean[:comma_idx + 1].strip()

        # 如果都没有，强制截断
        return clean[:35] + '...'

    return clean
