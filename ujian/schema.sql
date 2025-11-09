CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE students (
    nis VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    grade VARCHAR(10) NOT NULL,
    class VARCHAR(10) NOT NULL
);

CREATE TABLE teachers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    job jsonb NOT NULL
);

CREATE TABLE exam_forms (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  grade text NOT NULL,
  subject text NOT NULL,
  payload jsonb NOT NULL
);

CREATE TABLE sessions (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  nis text NOT NULL REFERENCES students(nis),
  subject text NOT NULL,
  active boolean NOT NULL DEFAULT false,
  seed text NOT NULL,
  session_hash text NOT NULL UNIQUE,
  special_key text NOT NULL,
  started_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE answers (
  id uuid PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
  nis text NOT NULL REFERENCES students(nis),
  session_hash text NOT NULL REFERENCES sessions(session_hash),
  subject text NOT NULL,
  answers jsonb NOT NULL,
  submitted_at timestamptz NOT NULL DEFAULT now()
);


-- prevent more than one active session per nis
CREATE UNIQUE INDEX uniq_active_nis ON sessions(nis) WHERE active = true;
