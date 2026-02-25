import datetime

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from data.connection import db_cursor
from data.users import User

from psycopg2.errors import UniqueViolation

@dataclass
class Bloom:
    id: int
    sender: User
    content: str
    sent_timestamp: datetime.datetime
    rebloom_from: Optional[str] = None
    rebloomed_by: Optional[any] = None
    rebloom_count: int = 0


def add_bloom(*, sender: User, content: str) -> Bloom:
    hashtags = [word[1:] for word in content.split(" ") if word.startswith("#")]

    now = datetime.datetime.now(tz=datetime.UTC)
    bloom_id = int(now.timestamp() * 1000000)
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO blooms (id, sender_id, content, send_timestamp) VALUES (%(bloom_id)s, %(sender_id)s, %(content)s, %(timestamp)s)",
            dict(
                bloom_id=bloom_id,
                sender_id=sender.id,
                content=content,
                timestamp=datetime.datetime.now(datetime.UTC),
            ),
        )
        for hashtag in hashtags:
            cur.execute(
                "INSERT INTO hashtags (hashtag, bloom_id) VALUES (%(hashtag)s, %(bloom_id)s)",
                dict(hashtag=hashtag, bloom_id=bloom_id),
            )

def add_rebloom(*, rebloomer: User, original_bloom_id: int) -> Optional[Bloom]:
    # Fetch original bloom from DB

    with db_cursor() as cur:
        cur.execute(
            """
            SELECT blooms.id, users.id, users.username, content, send_timestamp
            FROM blooms
            INNER JOIN users ON users.id = blooms.sender_id
            WHERE blooms.id =%s
            """,
            (original_bloom_id,)
        )
        row = cur.fetchone()

    if row is None:
        return None
    
    _, _, _, original_content, _ = row

    # New bloom id & timestamp
    now = datetime.datetime.now(tz=datetime.UTC)
    new_bloom_id = int(now.timestamp() * 1000000)

    try:
        # Insert new bloom as a "repost" of the original
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO blooms (id, sender_id, content, send_timestamp, rebloom_from, rebloom_by)
                VALUES (%(id)s, %(sender_id)s, %(content)s, %(timestamp)s, %(rebloom_from)s, %(rebloom_by)s)
                """,
                dict(
                    id=new_bloom_id,
                    sender_id=rebloomer.id,
                    content=original_content,
                    timestamp=now,
                    rebloom_from=original_bloom_id,
                    rebloom_by=rebloomer.id,
                ),
            )
    except UniqueViolation:
        raise ValueError("You have already rebloomed this bloom.")

    # Return the new rebloom
    return Bloom(
        id=new_bloom_id,
        sender=rebloomer,
        content=original_content,
        sent_timestamp=now,
        rebloomed_by=rebloomer,
        rebloom_count=0,
    )

def get_blooms_for_user(
    username: str, *, before: Optional[int] = None, limit: Optional[int] = None
) -> List[Bloom]:
    with db_cursor() as cur:
        kwargs = {
            "sender_username": username,
        }
        if before is not None:
            before_clause = "AND send_timestamp < %(before_limit)s"
            kwargs["before_limit"] = before
        else:
            before_clause = ""

        limit_clause = make_limit_clause(limit, kwargs)

        cur.execute(
            f"""SELECT
              blooms.id, users.username, blooms.content, blooms.send_timestamp,
              blooms.rebloom_from, rebloomer.username, original_sender.username,
              (
                SELECT COUNT(*)
                FROM blooms r
                WHERE r.rebloom_from = COALESCE(blooms.rebloom_from, blooms.id)
              )
            FROM
              blooms
              INNER JOIN users ON users.id = blooms.sender_id
              LEFT JOIN users AS rebloomer ON rebloomer.id = blooms.rebloom_by
              LEFT JOIN blooms AS original_bloom ON original_bloom.id = blooms.rebloom_from
              LEFT JOIN users AS original_sender ON original_sender.id = original_bloom.sender_id
            WHERE
              users.username = %(sender_username)s
              {before_clause}
            ORDER BY blooms.send_timestamp DESC
            {limit_clause}
            """,
            kwargs,
        )
        rows = cur.fetchall()
        blooms = []
        for row in rows:
            bloom_id, sender_username, content, timestamp, rebloom_from_id, rebloomed_by_username, original_sender_username, rebloom_count = row
            blooms.append(
                Bloom(
                    id=bloom_id,
                    sender=sender_username,
                    content=content,
                    sent_timestamp=timestamp,
                    rebloom_from=original_sender_username,
                    rebloomed_by=rebloomed_by_username,
                    rebloom_count= rebloom_count or 0
                )
            )
    return blooms


def get_bloom(bloom_id: int) -> Optional[Bloom]:
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT blooms.id, users.username, blooms.content, blooms.send_timestamp, blooms.rebloom_from, rebloomer.username, original_sender.username,
            (
              SELECT COUNT(*) 
              FROM blooms r
              WHERE r.rebloom_from = COALESCE(blooms.rebloom_from, blooms.id)
            ) AS rebloom_count
            FROM 
              blooms 
              INNER JOIN users ON users.id = blooms.sender_id
              LEFT JOIN users AS rebloomer ON rebloomer.id = blooms.rebloom_by 
              LEFT JOIN blooms AS original_bloom on original_bloom.id = blooms.rebloom_from
              LEFT JOIN users AS original_sender on original_sender.id = original_bloom.sender_id
            WHERE blooms.id = %s
            """,
            (bloom_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        bloom_id, sender_username, content, timestamp, _, rebloomed_by_username, original_sender_username, rebloom_count = row
        return Bloom(
            id=bloom_id,
            sender=sender_username,
            content=content,
            sent_timestamp=timestamp,
            rebloom_from=original_sender_username,
            rebloomed_by=rebloomed_by_username,
            rebloom_count= rebloom_count or 0,
        )


def get_blooms_with_hashtag(
    hashtag_without_leading_hash: str, *, limit: int = None
) -> List[Bloom]:
    kwargs = {
        "hashtag_without_leading_hash": hashtag_without_leading_hash,
    }
    limit_clause = make_limit_clause(limit, kwargs)
    with db_cursor() as cur:
        cur.execute(
            f"""SELECT
              blooms.id, users.username, content, send_timestamp
            FROM
              blooms INNER JOIN hashtags ON blooms.id = hashtags.bloom_id INNER JOIN users ON blooms.sender_id = users.id
            WHERE
              hashtag = %(hashtag_without_leading_hash)s
            ORDER BY send_timestamp DESC
            {limit_clause}
            """,
            kwargs,
        )
        rows = cur.fetchall()
        blooms = []
        for row in rows:
            bloom_id, sender_username, content, timestamp = row
            blooms.append(
                Bloom(
                    id=bloom_id,
                    sender=sender_username,
                    content=content,
                    sent_timestamp=timestamp,
                )
            )
    return blooms


def make_limit_clause(limit: Optional[int], kwargs: Dict[Any, Any]) -> str:
    if limit is not None:
        limit_clause = "LIMIT %(limit)s"
        kwargs["limit"] = limit
    else:
        limit_clause = ""
    return limit_clause
