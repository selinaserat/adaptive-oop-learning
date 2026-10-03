# Database integration contract

Implement the Python Repository protocol in `app/repositories/base.py`. `SQLRepository` is deliberately an unimplemented integration seam; no database vendor or schema has been assumed. Routes and LearningService depend only on that protocol. Construct the SQL adapter in `run.py` and pass it to `create_app(repository=SQLRepository(...))`. Set persistent=True only for shared durable storage. Keep credentials in environment configuration.

## Records and methods

| Method | Contract |
|---|---|
| transaction(student_id=None) | Context manager; atomic commit on success, rollback on any exception; serialize concurrent updates for the same student. Must support nested calls (dashboard/progress inside assessment). Nested contexts join the same transaction, never commit independently. |
| get_topics() | All topics sorted by topic_id, each a dict with topic_id, title, description, prerequisites (list of integer IDs), lesson (content/format dict). |
| get_topic(topic_id) | Same dict or None. |
| get_questions(topic_id) | List of private question dicts: question_id, question, options label-to-text dict, answer valid label. |
| get_diagnostic_questions() | Same question dicts plus topic_id; initial diagnostic uses every quiz question. Always nonempty and IDs unique. |
| create_student(name) | Atomically create student with generated integer ID, name, ISO UTC created_at, diagnostic_completed=False; return its dict. |
| get_student(student_id) | Student dict or None. |
| mark_diagnostic_completed(student_id) | Set diagnostic_completed=True inside current transaction. |
| get_progress(student_id) | Return a Progress dataclass for every current topic; synthesize not_started/null scores if no row exists. |
| update_progress(student_id, progress) | Upsert one topic's Progress within current transaction. |
| add_attempt(student_id, attempt) | Append immutable attempt, generating globally unique integer attempt_id and UTC created_at; return full record including student_id. Input includes kind, topic_id, correct_count, question_count, score, topic_results. |
| get_attempts_for_student(student_id) | All attempts ordered by created_at then attempt_id, oldest first. |

Return detached records so callers cannot accidentally mutate stored data. Service validates student existence before progress/attempt operations. Repository failures propagate to a generic 500; never leak connection strings or SQL details. Student creation must remain safe across workers; use database-generated IDs. Use connection pooling supported by the chosen database library, parameterized queries, migrations, and foreign keys.

## Suggested logical tables

- students: student_id PK, name, created_at, diagnostic_completed.
- topics: topic_id PK, title, description, lesson content/format (or separate lessons table).
- topic_prerequisites: topic_id + prerequisite_topic_id composite PK, both topic FKs.
- questions: question_id PK, topic_id FK, question text, private answer label; options in JSON or normalized question_options table.
- student_progress: student_id + topic_id composite PK; state enum/check, best_score and latest_score nullable numeric.
- attempts: attempt_id PK, student_id FK, kind enum, topic_id nullable FK, correct_count, question_count, score, created_at.
- attempt_topic_results: attempt_id + topic_id composite PK, score, correct_count, question_count, state snapshot.

Enforce score 0–100, valid states, nonnegative counts, correct_count <= question_count, and question_count > 0. Index attempts by student_id/created_at/attempt_id. Do not store or expose answer keys in public student views. Decide on assessment versioning before changing questions while students are using the system, since present history stores summary scores rather than question versions.

## SQL teammate handoff checklist

Provide the SQL dialect and server version, complete DDL/schema, primary/foreign keys and constraints, migration and seed scripts, the ORM/driver choice, a schema-to-record mapping, local database setup instructions, and secure environment variable names for connection details. Include curriculum/questions/options/private answer seeds with the existing IDs and the complete prerequisite graph. Explain transaction isolation, student locking, nested transaction behavior, pooling, backup/restore, and test database provisioning. Share credentials securely outside source control.

Then implement all protocol methods, run the repository conformance and API tests against a clean SQL test database, and add restart persistence, concurrent-submission, migration, and rollback integration tests. Replace the repository construction in run.py; route and service code stays intact. Authentication-related account fields need a separate agreement with the team.
