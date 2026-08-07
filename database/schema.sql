CREATE TABLE course (
    id SERIAL PRIMARY KEY,
    course_code VARCHAR(20) UNIQUE NOT NULL,
    course_name VARCHAR(200) NOT NULL,
    semester INTEGER NOT NULL,
    active BOOLEAN DEFAULT TRUE
);

CREATE TABLE topic (
    id SERIAL PRIMARY KEY,
    course_id INTEGER NOT NULL REFERENCES course(id),
    name VARCHAR(200) NOT NULL,
    importance NUMERIC(4,1) CHECK (importance BETWEEN 0 AND 10),
    estimated_hours NUMERIC(5,2) NOT NULL CHECK (estimated_hours > 0),
    learning_order INTEGER NOT NULL,
    UNIQUE (course_id, name)
);

CREATE TABLE topic_dependency (
    id SERIAL PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES topic(id),
    prerequisite_topic_id INTEGER NOT NULL REFERENCES topic(id)
);

CREATE TABLE pyq_question (
    id SERIAL PRIMARY KEY,
    course_id INTEGER NOT NULL REFERENCES course(id),
    topic_id INTEGER NOT NULL REFERENCES topic(id),
    subtopic VARCHAR(200),
    year INTEGER NOT NULL,
    marks NUMERIC(4,1) NOT NULL CHECK (marks > 0),
    question_text TEXT NOT NULL
);