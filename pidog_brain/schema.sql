-- PiDog Brain Database Schema
-- SQLite with FTS5 for full-text search

-- Memories table: people, facts, preferences, experiences
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL CHECK(category IN ('person', 'fact', 'preference', 'experience', 'location')),
    subject TEXT NOT NULL,
    content TEXT NOT NULL,
    importance REAL DEFAULT 0.5 CHECK(importance >= 0.0 AND importance <= 1.0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 0
);

-- FTS5 virtual table for fast full-text search on memories
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    subject,
    content,
    content='memories',
    content_rowid='id'
);

-- Triggers to keep FTS index in sync
CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, subject, content) VALUES (new.id, new.subject, new.content);
END;

CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, subject, content) VALUES('delete', old.id, old.subject, old.content);
END;

CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, subject, content) VALUES('delete', old.id, old.subject, old.content);
    INSERT INTO memories_fts(rowid, subject, content) VALUES (new.id, new.subject, new.content);
END;

-- Conversations table: compressed summaries of past interactions
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    summary TEXT NOT NULL,
    participant TEXT,
    mood TEXT,
    topics TEXT,  -- JSON array of topics discussed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tricks table: learned action sequences
CREATE TABLE IF NOT EXISTS tricks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    trigger_phrase TEXT NOT NULL,
    actions TEXT NOT NULL,  -- JSON array of actions
    times_performed INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_performed TIMESTAMP
);

-- Goals table: autonomous objectives with priority
CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT NOT NULL,
    priority INTEGER DEFAULT 3 CHECK(priority >= 1 AND priority <= 5),
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'completed', 'abandoned')),
    progress TEXT,  -- JSON object for tracking progress
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Faces table: stored face encodings for recognition
CREATE TABLE IF NOT EXISTS faces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    encoding BLOB NOT NULL,  -- 128-dimensional face encoding as bytes
    image_hash TEXT,  -- Hash of source image for deduplication
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    times_seen INTEGER DEFAULT 1
);

-- Rooms table: learned locations with visual descriptions
CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT NOT NULL,  -- Claude-generated description of room features
    landmarks TEXT,  -- JSON array of notable visual landmarks
    image_hash TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_visited TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    times_visited INTEGER DEFAULT 1
);

-- Observations table: recent sensor readings for novelty detection
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor_type TEXT NOT NULL,
    value TEXT NOT NULL,  -- JSON for complex values
    novelty_score REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Keep only recent observations (auto-cleanup via application)
CREATE INDEX IF NOT EXISTS idx_observations_created ON observations(created_at);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
CREATE INDEX IF NOT EXISTS idx_memories_subject ON memories(subject);
CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance DESC);
CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status);
CREATE INDEX IF NOT EXISTS idx_goals_priority ON goals(priority DESC);
CREATE INDEX IF NOT EXISTS idx_faces_name ON faces(name);
CREATE INDEX IF NOT EXISTS idx_rooms_name ON rooms(name);
