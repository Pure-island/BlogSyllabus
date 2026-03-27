from sqlmodel import Session, select

from app.db import create_db_and_tables, engine
from app.models import Source

DEFAULT_SOURCES = [
    {
        "name": "Hugging Face Blog",
        "homepage_url": "https://huggingface.co/blog",
        "rss_url": "https://huggingface.co/blog/feed.xml",
        "language": "en",
        "priority": 10,
    },
    {
        "name": "Lil'Log",
        "homepage_url": "https://lilianweng.github.io/",
        "rss_url": "https://lilianweng.github.io/index.xml",
        "language": "en",
        "priority": 20,
    },
    {
        "name": "BAIR Blog",
        "homepage_url": "https://bair.berkeley.edu/blog/",
        "rss_url": "https://bair.berkeley.edu/blog/feed.xml",
        "language": "en",
        "priority": 30,
    },
    {
        "name": "科学空间",
        "homepage_url": "https://kexue.fm/",
        "rss_url": "https://kexue.fm/feed",
        "language": "zh-CN",
        "priority": 15,
    },
]


def main() -> None:
    create_db_and_tables()

    with Session(engine) as session:
        existing_urls = set(session.exec(select(Source.rss_url)).all())
        for source_data in DEFAULT_SOURCES:
            if source_data["rss_url"] in existing_urls:
                continue
            session.add(Source(**source_data))

        session.commit()


if __name__ == "__main__":
    main()
