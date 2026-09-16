CREATE TABLE category (
    id    BIGINT AUTO_INCREMENT PRIMARY KEY,
    name  VARCHAR(60) NOT NULL UNIQUE,
    color VARCHAR(7)
);

CREATE TABLE calendar_event (
    id               BIGINT AUTO_INCREMENT PRIMARY KEY,
    version          BIGINT       NOT NULL DEFAULT 0,
    title            VARCHAR(200) NOT NULL,
    start_time       TIMESTAMP    NOT NULL,
    end_time         TIMESTAMP    NOT NULL,
    description      VARCHAR(2000),
    location         VARCHAR(200),
    color            VARCHAR(20),
    category_id      BIGINT REFERENCES category (id),
    reminder_minutes INT,
    reminded         BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMP,
    updated_at       TIMESTAMP
);

CREATE INDEX idx_calendar_event_range ON calendar_event (start_time, end_time);
