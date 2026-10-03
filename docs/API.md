# Frontend API contract

Base URL: `http://127.0.0.1:5000/api` locally. All response bodies are JSON. Send `Content-Type: application/json` for POST. IDs are positive integers; answer object keys are decimal question IDs as strings. No authentication is implemented yet: student IDs currently identify records, not authenticated sessions. Agree on login and authorization before public student use. CORS is an origin policy, not authentication.

## Endpoints

| Method | Path (relative to /api) | Success response | Status |
|---|---|---|---|
| GET | /health | `{"status":"ok","service":"adaptive-oop-learning"}` | 200 |
| GET | /topics | `{"topics":[Topic,...]}` | 200 |
| GET | /topics/{topic_id} | `{"topic":Topic}` | 200 |
| GET | /topics/{topic_id}/quiz | `{"topic_id":1,"topic_title":"Classes and Objects","questions":[Question,...]}` | 200 |
| GET | /diagnostic | `{"questions":[DiagnosticQuestion,...]}` | 200 |
| POST | /students | `{"student":Student}` | 201 |
| GET | /students/{student_id}/dashboard | Dashboard | 200 |
| POST | /students/{student_id}/diagnostic | AssessmentResult | 200 |
| POST | /students/{student_id}/topics/{topic_id}/quiz | AssessmentResult | 200 |
| GET | /students/{student_id}/progress | ProgressResponse | 200 |
| GET | /students/{student_id}/attempts | `{"attempts":[Attempt,...]}` | 200 |

The root `/` serves the Flask website preview. The former `/topics` and `/topics/1/quiz` paths are replaced by `/api` endpoints. All topic and question IDs from the original backend are preserved. Topic GET includes a lesson; a separate lesson route is unnecessary for this starter curriculum. Quiz GET is public curriculum retrieval; eligibility is enforced on submission.

## Data shapes

```json
{
  "topic_id": 1,
  "title": "Classes and Objects",
  "description": "Learn the basic relationship between classes and objects.",
  "prerequisites": [],
  "lesson": {"content": "Lesson text", "format": "plain_text"}
}
```

Question: `{"question_id":101,"question":"What is a class?","options":{"A":"A blueprint for creating objects","B":"A loop","C":"A database","D":"An error message"}}`.
DiagnosticQuestion adds `"topic_id":1`. Render option text as text, not HTML. No endpoint returns answer keys or per-question correctness.

Student: `{"student_id":1,"name":"Selina","created_at":"2026-10-03T22:00:00+00:00","diagnostic_completed":false}`.
Dates are ISO 8601 UTC. Student POST accepts exactly `{"name":"Selina"}`; trimmed name length is 1–100 characters. There is no uniqueness restriction on names.

Progress item: `{"topic_id":1,"state":"in_progress","best_score":50.0,"latest_score":50.0,"unlocked":true}`. State is `not_started`, `in_progress`, or `mastered`. Unattempted scores are null. `unlocked` means all prerequisites are mastered; a completed diagnostic is also required to submit quizzes.

Recommendation: `{"action":"review","topic_id":1,"reason":"Review and retry"}`. Actions:

- `take_diagnostic`: topic_id null; diagnostic has not been completed.
- `review`: retry the given eligible topic with prior unsuccessful performance.
- `start_topic`: begin the given eligible topic.
- `completed`: topic_id null; every topic is mastered.

ProgressResponse: `{"mastery_threshold":80,"progress":[ProgressItem,...],"recommendation":Recommendation}`.
Dashboard adds `"student":Student` to ProgressResponse.

Attempt: `{"attempt_id":1,"student_id":1,"kind":"quiz","topic_id":1,"correct_count":2,"question_count":2,"score":100.0,"topic_results":[{"topic_id":1,"state":"mastered","correct_count":2,"question_count":2,"score":100.0}],"created_at":"2026-10-03T22:00:00+00:00"}`.
A diagnostic attempt has kind `diagnostic`, topic_id null, and one topic_result for every assessed topic. `state` records the state at submission time. History is ordered oldest first. Submitted options are not stored or returned in this initial version.

AssessmentResult: `{"attempt":Attempt,"mastery_threshold":80,"progress":[ProgressItem,...],"recommendation":Recommendation}`.

## Submission examples and rules

Quiz request for topic 1:
```json
{"answers":{"101":"A","102":"B"}}
```
Diagnostic request:
```json
{"answers":{"101":"A","102":"B","201":"A","202":"B","301":"A","302":"A"}}
```
These examples follow the supplied starter curriculum. The frontend obtains IDs and available labels from GET responses. It sends selected labels and never an official score or mastery value. The backend requires exactly all question IDs for that assessment and one valid, case-sensitive option label per question. Missing, extra, wrong-type, or invalid options yield 400 with no writes. Extra root fields are rejected. Questions cannot be partially submitted.

Scoring uses correct/total × 100; response percentages round to two decimal places. Mastery compares the unrounded fraction against 80%. Current two-question quizzes can yield only 0%, 50%, or 100%; add questions for finer measurement. Overall diagnostic score is weighted by question count. Topic diagnostic performance is evaluated independently. Diagnostic can establish mastery without prior prerequisites; dependent quizzes still require every prerequisite to be mastered. Unsuccessful diagnostic topics become in_progress. Diagnostic retakes are allowed and append history.

Mastery is retained after later lower scores; latest_score updates and best_score never decreases. The recommendation chooses eligible in_progress topics first, then other eligible unmastered topics, breaking ties by ascending topic ID. This supports new topics with arbitrary acyclic prerequisite lists.

## Error contract

```json
{"error":{"code":"prerequisites_not_met","message":"Master prerequisite topics first","details":{"missing_topic_ids":[1]}}}
```

| HTTP | Codes / conditions |
|---|---|
| 400 | invalid_request, invalid_name, invalid_answers, invalid_option; bad_request for malformed JSON |
| 403 | diagnostic_required, prerequisites_not_met |
| 404 | student_not_found, topic_not_found; not_found for unknown routes |
| 405 | method_not_allowed |
| 413 | request_entity_too_large (64 KiB request limit) |
| 415 | unsupported_media_type (POST without JSON Content-Type) |
| 500 | internal_error; details logged only on server |

`details` is optional. invalid_answers details include missing and unknown ID arrays. Student/topic checks precede scoring and prerequisite checks precede answer validation. OPTIONS preflight is supported. Only origins listed in FRONTEND_ORIGINS receive CORS permission; credentials/cookies are currently disabled.

POST retries are not idempotent: a successful repeat creates another attempt. Disable double submission in the UI; agree on idempotency keys before adding automatic retries. No pagination, enrollment, deletion, or assessment versioning is implemented yet.
