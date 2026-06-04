"""
OA Router — Handles Online Assessment result submission and follow-up workflows.
"""
from typing import Any, Dict, Optional
import logging
import os
import re
from urllib.parse import parse_qs, unquote, urlencode, urlparse, urlunparse

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from psycopg2.extras import RealDictCursor

from backend.database import get_db_connection
from backend.phase_logger import log_phase_completion
from backend.api.email_router import (
    OACompletionRequest,
    get_oa_completion_thank_you_email,
    send_email_via_smtp,
)

router = APIRouter(prefix="/oa", tags=["OA"])
webhook_router = APIRouter(tags=["OA"])
logger = logging.getLogger(__name__)

PASS_THRESHOLD_OUT_OF_10 = float(os.getenv("OA_PASS_THRESHOLD_OUT_OF_10", "6.0"))
ALLOW_HACKERRANK_QUERY_FALLBACK = os.getenv("OA_ALLOW_HACKERRANK_QUERY_FALLBACK", "false").lower() in (
    "1",
    "true",
    "yes",
    "on",
)

class OAResultSubmission(BaseModel):
    candidate_email: str
    candidate_name: Optional[str] = None
    score: Optional[float] = None
    report_url: Optional[str] = None
    total_questions: Optional[int] = None
    correct_answers: Optional[int] = None

class OAResultResponse(BaseModel):
    status: str
    message: str
    score: float
    candidate_email: str

def _normalize_score_out_of_10(value: float, denominator: Optional[float] = None) -> float:
    """Normalize a raw score to out-of-10 scale."""
    if denominator is not None:
        if denominator <= 0:
            raise ValueError("Invalid score denominator")
        normalized = (value / denominator) * 10.0
    else:
        if value <= 10:
            normalized = value
        elif value <= 100:
            normalized = value / 10.0
        else:
            raise ValueError(f"Score {value} is out of expected range")

    if normalized < 0 or normalized > 10:
        raise ValueError(f"Normalized score {normalized} is out of 0-10 range")

    return round(normalized, 2)

def _append_query_params(url: str, params: Dict[str, Optional[str]]) -> str:
    """Append or overwrite query parameters in a URL."""
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    for key, value in params.items():
        if value is None:
            continue
        text = str(value).strip()
        if text == "":
            continue
        query[key] = [text]

    updated_query = urlencode(query, doseq=True)
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            updated_query,
            parsed.fragment,
        )
    )

def _build_oa_callback_url(candidate_email: str, candidate_name: Optional[str]) -> str:
    base_callback = os.getenv("OA_COMPLETION_CALLBACK_URL")
    if not base_callback:
        public_base = (os.getenv("PUBLIC_API_BASE_URL") or "http://127.0.0.1:8000").rstrip("/")
        base_callback = f"{public_base}/oa/complete"

    return _append_query_params(
        base_callback,
        {
            "candidate_email": candidate_email,
            "candidate_name": candidate_name,
        },
    )

def _build_official_oa_redirect_url(
    target_oa_url: str,
    candidate_email: str,
    candidate_name: Optional[str],
) -> str:
    """
    Build official OA link with callback hints.

    Many OA platforms support one of: callback_url, redirect_url, return_url.
    Unknown params are typically ignored by platforms that do not support them.
    """
    callback_url = _build_oa_callback_url(candidate_email, candidate_name)
    return _append_query_params(
        target_oa_url,
        {
            "candidate_email": candidate_email,
            "candidate_name": candidate_name,
            "callback_url": callback_url,
            "redirect_url": callback_url,
            "return_url": callback_url,
            "state": candidate_email,
        },
    )

def _parse_score(raw_score: Any) -> float:
    """Parse score from raw text and normalize to out-of-10 scale."""
    if raw_score is None:
        raise ValueError("score is required")

    if isinstance(raw_score, (int, float)):
        return _normalize_score_out_of_10(float(raw_score))

    text = str(raw_score).strip()
    if not text:
        raise ValueError("score is empty")

    fraction = re.search(r"(-?\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", text)
    if fraction:
        value = float(fraction.group(1))
        denominator = float(fraction.group(2))
        return _normalize_score_out_of_10(value, denominator)

    percent = re.search(r"(-?\d+(?:\.\d+)?)\s*%", text)
    if percent:
        value = float(percent.group(1))
        return _normalize_score_out_of_10(value, 100.0)

    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        raise ValueError(f"Invalid score value: {raw_score}")

    return _normalize_score_out_of_10(float(match.group(0)))

def _as_optional_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def _normalize_submission(payload: Dict[str, Any]) -> OAResultSubmission:
    """Normalize multiple callback payload shapes into one submission model."""
    data = dict(payload or {})

    if isinstance(data.get("body"), dict):
        merged = dict(data["body"])
        for key, value in data.items():
            if key != "body":
                merged[key] = value
        data = merged

    candidate_email = (
        data.get("candidate_email")
        or data.get("candidateEmail")
        or data.get("email")
        or data.get("state")
    )
    if not candidate_email:
        raise HTTPException(status_code=422, detail="candidate_email is required")

    raw_score = data.get("score")
    if raw_score is None:
        raw_score = data.get("oa_score")
    if raw_score is None:
        raw_score = data.get("oaScore")
    if raw_score is None:
        raw_score = data.get("result")

    score = None
    if raw_score is not None:
        try:
            score = _parse_score(raw_score)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    report_url = (
        data.get("report_url")
        or data.get("reportUrl")
        or data.get("submission_url")
        or data.get("report")
        or data.get("exam_url")
        or data.get("examUrl")
        or data.get("assessment_url")
        or data.get("assessmentUrl")
        or data.get("url")
    )

    return OAResultSubmission(
        candidate_email=str(candidate_email).strip().lower(),
        candidate_name=(
            data.get("candidate_name")
            or data.get("candidateName")
            or data.get("name")
        ),
        score=score,
        report_url=report_url,
        total_questions=_as_optional_int(
            data.get("total_questions") or data.get("totalQuestions")
        ),
        correct_answers=_as_optional_int(
            data.get("correct_answers") or data.get("correctAnswers")
        ),
    )

def _score_from_url_tokens(report_url: str) -> Optional[float]:
    """Extract score from URL query/path conventions."""
    parsed = urlparse(report_url)

    query_params = parse_qs(parsed.query)
    for key in ("score", "oa_score", "result", "marks", "percentage", "percent"):
        values = query_params.get(key, [])
        for value in values:
            try:
                return _parse_score(value)
            except ValueError:
                continue

    decoded_url = unquote(report_url)
    token_patterns = [
        r"(?:oa|score|result)[-_/: ]+(\d{1,3}(?:\.\d+)?)",
        r"[?&](?:oa_score|score|result|marks)=(-?\d+(?:\.\d+)?)",
    ]
    for pattern in token_patterns:
        match = re.search(pattern, decoded_url, flags=re.IGNORECASE)
        if match:
            try:
                return _parse_score(match.group(1))
            except ValueError:
                continue

    return None

def _is_hackerrank_url(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
        return "hackerrank.com" in host
    except Exception:
        return False

def _score_from_hackerrank_page(report_url: str) -> Optional[float]:
    """Extract authoritative score directly from HackerRank page content."""
    try:
        response = httpx.get(
            report_url,
            timeout=float(os.getenv("OA_HACKERRANK_FETCH_TIMEOUT", "8.0")),
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Accept": "text/html,application/xhtml+xml,application/json",
            },
        )
        if response.status_code >= 400:
            logger.warning(
                "HackerRank page fetch failed (%s): %s",
                response.status_code,
                report_url,
            )
            return None

        body = response.text
        patterns = [
            r"\bScore\s*:\s*(\d+(?:\.\d+)?)\s*/\s*(10|100)",
            r"\bScore\s*:\s*(\d+(?:\.\d+)?)\b",
            r'"score"\s*:\s*(\d+(?:\.\d+)?)',
        ]

        for pattern in patterns:
            match = re.search(pattern, body, flags=re.IGNORECASE)
            if not match:
                continue

            try:
                value = float(match.group(1))
                denominator = None
                if len(match.groups()) >= 2 and match.group(2):
                    denominator = float(match.group(2))
                normalized = _normalize_score_out_of_10(value, denominator)
                logger.info(
                    "Parsed HackerRank score %.2f/10 from report page: %s",
                    normalized,
                    report_url,
                )
                return normalized
            except ValueError:
                continue
    except Exception as exc:
        logger.warning("Could not extract HackerRank page score from %s: %s", report_url, str(exc))

    return None

def _score_from_report_page(report_url: str) -> Optional[float]:
    """Best-effort extraction from report page content when URL tokens are absent."""
    try:
        response = httpx.get(
            report_url,
            timeout=float(os.getenv("OA_REPORT_FETCH_TIMEOUT", "8.0")),
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 OA-Score-Bot"},
        )
        if response.status_code >= 400:
            logger.warning("Report URL fetch failed (%s): %s", response.status_code, report_url)
            return None

        body = response.text
        patterns = [
            r"\b(?:score|overall score|final score|marks)\b[^\d]{0,30}(\d{1,3}(?:\.\d+)?)\s*/\s*(10|100)",
            r"\b(?:score|overall score|final score|marks)\b[^\d]{0,30}(\d{1,3}(?:\.\d+)?)\s*%",
            r'"(?:score|overallScore|finalScore|totalScore)"\s*:\s*"?(\d{1,3}(?:\.\d+)?)"?',
        ]
        for pattern in patterns:
            match = re.search(pattern, body, flags=re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1))
                    if len(match.groups()) >= 2 and match.group(2):
                        denominator = float(match.group(2))
                        return _normalize_score_out_of_10(value, denominator)
                    if "%" in match.group(0):
                        return _normalize_score_out_of_10(value, 100.0)
                    return _normalize_score_out_of_10(value)
                except ValueError:
                    continue
    except Exception as exc:
        logger.warning("Could not parse score from report page %s: %s", report_url, str(exc))

    return None

def _resolve_score(submission: OAResultSubmission) -> float:
    """Resolve score from payload, else derive from report/exam URL."""
    score: Optional[float] = None
    is_hackerrank_report = bool(submission.report_url and _is_hackerrank_url(submission.report_url))

    if submission.report_url:
        if is_hackerrank_report:

            score = _score_from_hackerrank_page(submission.report_url)

            if score is None and ALLOW_HACKERRANK_QUERY_FALLBACK:
                score = _score_from_url_tokens(submission.report_url)

            if score is None:
                score = _score_from_report_page(submission.report_url)
        else:
            if score is None:
                score = _score_from_url_tokens(submission.report_url)

            if score is None:
                score = _score_from_report_page(submission.report_url)

    if score is None and submission.score is not None:
        if is_hackerrank_report and not ALLOW_HACKERRANK_QUERY_FALLBACK:
            logger.warning(
                "Ignoring callback score value for HackerRank URL; waiting for authoritative page score"
            )
        else:
            score = float(submission.score)

    if score is None:
        if is_hackerrank_report:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Could not verify score directly from the official HackerRank submission/report page. "
                    "Please use the exact submission URL (with visible Score on page) or configure HackerRank API integration."
                ),
            )
        raise HTTPException(
            status_code=422,
            detail=(
                "Could not extract score from official OA link. "
                "Ensure HackerRank report URL is accessible and includes submission score details."
            ),
        )

    if score < 0 or score > 10:
        raise HTTPException(status_code=422, detail=f"Extracted score {score} is out of range (0-10)")

    return float(score)

def _resolve_report_url_for_callback(
    request: Request,
    provided_report_url: Optional[str],
) -> Optional[str]:
    """
    Pick the strongest report URL source from callback request.

    If provider doesn't send explicit report URL, use full callback URL so score
    can still be parsed from query tokens like ?result=85/100.
    """
    if provided_report_url and str(provided_report_url).strip():
        return str(provided_report_url).strip()

    referer = request.headers.get("referer") or request.headers.get("referrer")
    if referer and _is_hackerrank_url(referer):
        return referer

    return str(request.url)

def send_oa_completion_thank_you_email(
    candidate_email: str, 
    candidate_name: str, 
    score: float,
    report_url: Optional[str] = None
):
    """Generate and send OA completion email via configured SMTP credentials."""
    try:
        template = get_oa_completion_thank_you_email(
            OACompletionRequest(
                candidate_email=candidate_email,
                candidate_name=candidate_name,
                oa_score=round(score, 2),
                report_url=report_url,
            )
        )

        if template.get("skipped"):
            logger.warning(
                "OA completion email skipped for %s: %s",
                candidate_email,
                template.get("body", "unknown reason"),
            )
            return False

        success, message = send_email_via_smtp(
            recipient_email=template["recipient_email"],
            recipient_name=template.get("recipient_name", candidate_name),
            subject=template["subject"],
            body=template["body"],
            is_html=True,
        )

        if success:
            logger.info("OA completion email sent to %s", candidate_email)
        else:
            logger.error("OA completion email failed for %s: %s", candidate_email, message)
        return success
    except Exception as e:
        logger.exception("Error sending OA completion email for %s: %s", candidate_email, str(e))
        return False

def trigger_scheduling_workflow(candidate_email: str, candidate_name: str, score: float):
    """Trigger scheduling webhook after a passing score."""
    try:
        if score < PASS_THRESHOLD_OUT_OF_10:
            logger.info(
                "Score %.2f below threshold (%.2f), scheduling not triggered",
                score,
                PASS_THRESHOLD_OUT_OF_10,
            )
            return False

        schedule_webhook_url = (
            os.getenv("N8N_SCHEDULE_WEBHOOK_URL")
            or "http://localhost:5678/webhook/schedule-interviews"
        )

        payload = {
            "job_id": "OA-AUTO",
            "shortlisted_candidates": [
                {
                    "candidate_name": candidate_name,
                    "email": candidate_email,
                    "ai_score": round(score * 10.0, 2),
                }
            ],
            "candidate_email": candidate_email,
            "candidate_name": candidate_name,
            "oa_score": score,
            "oa_score_out_of_10": score,
            "oa_score_percent": round(score * 10.0, 2),
            "trigger_source": "oa_completion",
        }

        response = httpx.post(schedule_webhook_url, json=payload, timeout=30.0)

        if response.status_code == 200:
            logger.info("Scheduling workflow triggered for %s", candidate_email)
            return True

        logger.warning(
            "Scheduling webhook returned %s for %s: %s",
            response.status_code,
            candidate_email,
            response.text,
        )
        return False
    except Exception as e:
        logger.error("Error triggering scheduling workflow: %s", str(e))
        return False

def _process_oa_result(
    submission: OAResultSubmission,
    background_tasks: BackgroundTasks,
) -> OAResultResponse:
    conn = None
    try:
        resolved_score = _resolve_score(submission)
        conn = get_db_connection()

        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute(
                """
                SELECT id, candidate_name
                FROM resume_data
                WHERE lower(trim(email)) = lower(trim(%s))
                ORDER BY oa_completed_at DESC NULLS LAST, id DESC
                LIMIT 1
                """,
                (submission.candidate_email,),
            )
            candidate = cur.fetchone()

            candidate_name = (
                submission.candidate_name
                or (candidate.get("candidate_name") if candidate else None)
                or "Candidate"
            )

            cur.execute(
                """
                UPDATE resume_data
                SET oa_score = %s,
                    oa_status = %s,
                    oa_report_url = %s,
                    oa_completed_at = CURRENT_TIMESTAMP
                WHERE lower(trim(email)) = lower(trim(%s))
                """,
                (resolved_score, "completed", submission.report_url, submission.candidate_email),
            )

            if cur.rowcount == 0:

                cur.execute(
                    """
                    INSERT INTO resume_data (
                        candidate_name,
                        email,
                        oa_score,
                        oa_status,
                        oa_report_url,
                        oa_completed_at
                    ) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    RETURNING id, oa_score, oa_status
                    """,
                    (
                        candidate_name,
                        submission.candidate_email,
                        resolved_score,
                        "completed",
                        submission.report_url,
                    ),
                )
                result = cur.fetchone()
            else:
                cur.execute(
                    """
                    SELECT id, oa_score, oa_status
                    FROM resume_data
                    WHERE lower(trim(email)) = lower(trim(%s))
                    ORDER BY oa_completed_at DESC NULLS LAST, id DESC
                    LIMIT 1
                    """,
                    (submission.candidate_email,),
                )
                result = cur.fetchone()

            cur.execute(
                """
                UPDATE candidates
                SET oa_score = %s
                WHERE lower(trim(email)) = lower(trim(%s))
                """,
                (resolved_score, submission.candidate_email),
            )

            conn.commit()

            logger.info(
                "OA score updated immediately for %s -> %.2f",
                submission.candidate_email,
                resolved_score,
            )

            log_phase_completion(
                "OA Completion",
                f"candidate={submission.candidate_email} score={resolved_score}/10",
            )

            background_tasks.add_task(
                send_oa_completion_thank_you_email,
                candidate_email=submission.candidate_email,
                candidate_name=candidate_name,
                score=resolved_score,
                report_url=submission.report_url,
            )

            if resolved_score >= PASS_THRESHOLD_OUT_OF_10:
                background_tasks.add_task(
                    trigger_scheduling_workflow,
                    candidate_email=submission.candidate_email,
                    candidate_name=candidate_name,
                    score=resolved_score,
                )
                log_phase_completion(
                    "Interview Scheduling",
                    (
                        "source=oa_completion "
                        f"candidate={submission.candidate_email} score={resolved_score}/10"
                    ),
                )

            return OAResultResponse(
                status="success",
                message=(
                    f"OA score {resolved_score}/10 recorded from official exam/report URL and completion email sent/queued."
                ),
                score=resolved_score,
                candidate_email=submission.candidate_email,
            )
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error("Error processing OA result: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@router.post("/submit-result", response_model=OAResultResponse)
def submit_oa_result(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    """
    Submit OA result immediately after exam completion.
    - Updates resume_data with score in real-time
    - Sends thank you email
    - Triggers scheduling workflow if score >= 60
    """
    submission = _normalize_submission(payload)
    return _process_oa_result(submission, background_tasks)

@router.get("/launch")
def launch_official_oa(
    candidate_email: str = Query(...),
    candidate_name: Optional[str] = Query(None),
    target: Optional[str] = Query(None),
):
    """
    Tracking launcher for official OA links.

    Email should link here so we can attach callback hints and then redirect to
    the official OA platform URL.
    """
    target_oa_url = (
        target
        or os.getenv("OFFICIAL_OA_LINK")
        or os.getenv("DEFAULT_OA_LINK")
        or "https://hackerrank.com/sample-test"
    )

    redirect_url = _build_official_oa_redirect_url(
        target_oa_url=target_oa_url,
        candidate_email=candidate_email,
        candidate_name=candidate_name,
    )
    return RedirectResponse(url=redirect_url, status_code=302)

@router.post("/submit-result-webhook")
def submit_oa_result_webhook(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    """
    Alternative webhook endpoint for OA platform callbacks (e.g., HackerRank, Codilot).
    Same functionality as submit_oa_result but designed for external platform integration.
    """
    submission = _normalize_submission(payload)
    return _process_oa_result(submission, background_tasks)

@router.get("/complete", response_class=HTMLResponse)
def complete_official_oa_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    candidate_email: Optional[str] = Query(None),
    candidate_name: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    score: Optional[str] = Query(None),
    result: Optional[str] = Query(None),
    oa_score: Optional[str] = Query(None),
    report_url: Optional[str] = Query(None),
    report: Optional[str] = Query(None),
    submission_url: Optional[str] = Query(None),
):
    """
    Completion callback endpoint expected from official OA platform redirect.

    This endpoint updates the DB from callback URL data (score/result/report URL)
    and sends the completion email.
    """
    payload: Dict[str, Any] = {
        "candidate_email": candidate_email or state,
        "candidate_name": candidate_name,
        "score": score or oa_score or result,
        "report_url": _resolve_report_url_for_callback(
            request,
            report_url or report or submission_url,
        ),
    }

    try:
        submission = _normalize_submission(payload)
        result_data = _process_oa_result(submission, background_tasks)
        return HTMLResponse(
            content=(
                "<html><body style='font-family:Arial,sans-serif;padding:24px;'>"
                "<h2>Assessment Submitted</h2>"
                f"<p>Your score has been recorded: <strong>{result_data.score}/10</strong>.</p>"
                "<p>Thank you for completing the assessment.</p>"
                "</body></html>"
            ),
            status_code=200,
        )
    except HTTPException as exc:
        return HTMLResponse(
            content=(
                "<html><body style='font-family:Arial,sans-serif;padding:24px;'>"
                "<h2>Assessment Callback Error</h2>"
                f"<p>{exc.detail}</p>"
                "</body></html>"
            ),
            status_code=exc.status_code,
        )

@router.post("/results", response_model=OAResultResponse)
def submit_oa_result_alias(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    """Compatibility alias for OA result callback integrations."""
    submission = _normalize_submission(payload)
    return _process_oa_result(submission, background_tasks)

@router.post("/submit-from-url", response_model=OAResultResponse)
def submit_oa_result_from_url(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    """Explicit URL-first endpoint: score is extracted from report/exam URL."""
    submission = _normalize_submission(payload)
    return _process_oa_result(submission, background_tasks)

@webhook_router.post("/webhook/oa-results", response_model=OAResultResponse)
@webhook_router.post("/oa-results", response_model=OAResultResponse)
def submit_oa_result_compat(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    """Handle legacy callback paths without requiring workflow changes."""
    submission = _normalize_submission(payload)
    return _process_oa_result(submission, background_tasks)

@router.get("/candidate/{candidate_email}/status")
def get_candidate_oa_status(candidate_email: str):
    """Get OA status and score for a candidate."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT 
                    id,
                    candidate_name,
                    email,
                    oa_status,
                    oa_score,
                    oa_report_url,
                    oa_completed_at
                FROM resume_data 
                WHERE lower(trim(email)) = lower(trim(%s))
                ORDER BY oa_completed_at DESC NULLS LAST, id DESC
                LIMIT 1
                """,
                (candidate_email,)
            )
            candidate = cur.fetchone()

            if not candidate:
                raise HTTPException(status_code=404, detail="Candidate not found")

            return {
                "candidate_name": candidate["candidate_name"],
                "email": candidate["email"],
                "oa_status": candidate["oa_status"],
                "oa_score": candidate["oa_score"],
                "oa_report_url": candidate["oa_report_url"],
                "oa_completed_at": candidate.get("oa_completed_at"),
                "passed": candidate["oa_score"] >= PASS_THRESHOLD_OUT_OF_10 if candidate["oa_score"] is not None else False,
                "score_scale": "out_of_10",
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching OA status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()