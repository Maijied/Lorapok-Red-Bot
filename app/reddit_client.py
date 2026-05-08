import logging

import praw

from app.config import Settings

logger = logging.getLogger(__name__)


def get_reddit(settings: Settings) -> praw.Reddit:
    reddit = praw.Reddit(
        client_id=settings.reddit_client_id,
        client_secret=settings.reddit_client_secret,
        username=settings.reddit_username,
        password=settings.reddit_password,
        user_agent=settings.reddit_user_agent,
    )
    me = reddit.user.me()
    if me is None:
        raise RuntimeError("Reddit authentication failed.")
    logger.info("Authenticated Reddit account: %s", me)
    return reddit
