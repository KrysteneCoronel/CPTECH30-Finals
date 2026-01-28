CREATE TABLE IF NOT EXISTS memes (
    id CHAR(36) NOT NULL PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL,
    s3_key VARCHAR(255) NOT NULL,
    description TEXT,
    privacy ENUM('public', 'private') NOT NULL DEFAULT 'public',
    file_type VARCHAR(50) DEFAULT NULL,
    file_size_bytes INT UNSIGNED DEFAULT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_memes_user_privacy (user_id, privacy, created_at),
    INDEX idx_memes_privacy_created (privacy, created_at),
    CONSTRAINT fk_memes_users FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE ON UPDATE CASCADE
);