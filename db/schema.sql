CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR NOT NULL,
    password_salt BYTEA NOT NULL,
    password_scrypt BYTEA NOT NULL,
    UNIQUE(username)
);

CREATE TABLE blooms (
    id BIGSERIAL NOT NULL PRIMARY KEY,
    sender_id INT NOT NULL REFERENCES users(id),
    content TEXT NOT NULL,
    send_timestamp TIMESTAMP NOT NULL,
    rebloom_from BIGINT REFERENCES blooms(id),
    rebloom_by INT REFERENCES users(id)
);

CREATE UNIQUE INDEX unique_rebloom
ON blooms (rebloom_from, rebloom_by)
WHERE rebloom_from IS NOT NULL;

CREATE TABLE follows (
    id SERIAL PRIMARY KEY,
    follower INT NOT NULL REFERENCES users(id),
    followee INT NOT NULL REFERENCES users(id),
    UNIQUE(follower, followee)
);

CREATE TABLE hashtags (
    id SERIAL PRIMARY KEY,
    hashtag VARCHAR NOT NULL,
    bloom_id BIGINT NOT NULL REFERENCES blooms(id),
    UNIQUE(hashtag, bloom_id)
);
