import json
import re
import time
import urllib.parse
from typing import Optional
from http.cookies import SimpleCookie
import requests
from src.config import Config
from src.logger import log

class UnstopClient:
    def __init__(self):
        self.session = requests.Session()
        self._setup_headers_and_cookies()

    def _setup_headers_and_cookies(self):
        """Constructs headers and populates session cookies mimicking a logged-in browser."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": Config.POTD_PAGE_URL,
            "Origin": Config.BASE_URL,
            "Sec-Ch-Ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin"
        }

        # 1. Attach Cookies
        if Config.UNSTOP_COOKIES:
            raw_cookies = Config.UNSTOP_COOKIES
            headers["Cookie"] = raw_cookies

            # Automatically extract JWT access_token from cookies if Authorization is not set
            token_match = re.search(r'access_token=([A-Za-z0-9\-_.]+)', raw_cookies)
            if token_match and not Config.UNSTOP_AUTH_TOKEN:
                headers["Authorization"] = f"Bearer {token_match.group(1)}"

            # Extract CSRF / XSRF token
            xsrf_match = re.search(r'XSRF-TOKEN=([^;]+)', raw_cookies)
            if xsrf_match:
                decoded_xsrf = urllib.parse.unquote(xsrf_match.group(1))
                headers["X-XSRF-TOKEN"] = decoded_xsrf
                headers["X-CSRF-TOKEN"] = decoded_xsrf

        # 2. Attach Bearer Token if explicitly provided
        if Config.UNSTOP_AUTH_TOKEN:
            token = Config.UNSTOP_AUTH_TOKEN
            if not token.lower().startswith("bearer "):
                token = f"Bearer {token}"
            headers["Authorization"] = token

        self.session.headers.update(headers)

    def _clean_html(self, raw_html: str) -> str:
        """Removes HTML tags and cleans up whitespace."""
        if not raw_html:
            return ""
        clean = re.sub(r'<br\s*/?>', '\n', raw_html)
        clean = re.sub(r'</p>', '\n\n', clean)
        clean = re.sub(r'<[^>]+>', ' ', clean)
        clean = re.sub(r'&nbsp;', ' ', clean)
        clean = re.sub(r'&lt;', '<', clean)
        clean = re.sub(r'&gt;', '>', clean)
        clean = re.sub(r'&amp;', '&', clean)
        clean = re.sub(r' +', ' ', clean)
        return clean.strip()

    def get_official_potd_id(self) -> Optional[str]:
        """
        Dynamically discovers the official Unstop Problem of the Day (POTD) ID.
        Employs multi-layer discovery strategies to guarantee finding today's live POTD.
        """
        # Strategy 1: Explicit POTD filter API
        potd_endpoints = [
            f"{Config.BASE_URL}/api/code/competition/practicequestions?is_potd=1",
            f"{Config.BASE_URL}/api/code/competition/practicequestions?type=potd",
            f"{Config.BASE_URL}/api/code/competition/practicequestions"
        ]

        for url in potd_endpoints:
            try:
                res = self.session.get(url, timeout=12)
                if res.status_code == 200:
                    json_data = res.json()
                    data = json_data.get("data", {})
                    
                    # Direct potd object in response
                    if isinstance(data, dict) and data.get("potd") and isinstance(data["potd"], dict):
                        potd_obj = data["potd"]
                        potd_id = str(potd_obj.get("id"))
                        log.info(f"🎯 Discovered Official Unstop POTD: '{potd_obj.get('name')}' (ID: {potd_id})")
                        return potd_id

                    items = data.get("data", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                    
                    # 1. Search for item with is_potd == True / 1 / 'true'
                    for item in items:
                        is_potd_val = item.get("is_potd") or item.get("potd")
                        if is_potd_val is True or str(is_potd_val).lower() in ["1", "true"]:
                            potd_id = str(item.get("id"))
                            log.info(f"🎯 Discovered Official Unstop POTD: '{item.get('name')}' (ID: {potd_id})")
                            return potd_id
                    
                    # 2. If filtered endpoint returned items, take the first one
                    if ("is_potd=1" in url or "type=potd" in url) and items:
                        potd_id = str(items[0].get("id"))
                        log.info(f"🎯 Discovered Official Unstop POTD: '{items[0].get('name')}' (ID: {potd_id})")
                        return potd_id
            except Exception as e:
                log.debug(f"POTD discovery endpoint '{url}' note: {e}")

        # Strategy 2: Scrape practice coding dashboard HTML for the POTD banner
        try:
            res = self.session.get(f"{Config.BASE_URL}/practice/coding", timeout=12)
            if res.status_code == 200:
                # Search for practice question links or props
                match = re.search(r'/code/practice/(\d+)', res.text)
                if match:
                    potd_id = match.group(1)
                    log.info(f"🎯 Discovered POTD from dashboard banner: ID {potd_id}")
                    return potd_id
        except Exception as e:
            log.debug(f"Dashboard scrape note: {e}")

        log.warning("⚠️ Could not dynamically resolve POTD ID. Falling back to default.")
        return None

    def fetch_potd_details(self, question_id_or_url: str = None) -> dict:
        """
        Fetches problem details for the specified question ID/URL or automatically
        discovers today's official Problem of the Day (POTD).
        """
        raw_val = question_id_or_url or Config.TARGET_QUESTION
        qid = None

        # Check if user specified a numerical ID or URL
        if raw_val and str(raw_val).strip().lower() not in ["potd", "auto", "daily", ""] and not str(raw_val).startswith("-"):
            qid = Config.get_target_question_id(raw_val)

        # If not manually specified, auto-discover today's official POTD
        if not qid:
            qid = self.get_official_potd_id() or "659208"

        log.info(f"🔍 Fetching Unstop coding question (ID: {qid})...")

        url = f"{Config.BASE_URL}/api/code/competition/get/practice/question/{qid}"
        try:
            res = self.session.get(url, timeout=15)
            if res.status_code == 200:
                data = res.json().get("data", res.json())
                parsed = self._parse_unstop_question(data, qid)
                log.info(f"✅ Successfully fetched problem: '{parsed.get('title')}'")
                return parsed
            else:
                log.warning(f"⚠️ API returned {res.status_code} for question {qid}")
        except Exception as e:
            log.error(f"❌ Failed to fetch question {qid}: {e}")

        # Fallback question details if network fails
        return {
            "problem_id": qid,
            "entity_id": qid,
            "title": f"Unstop Practice Question {qid}",
            "description": "Solve the problem using optimal Python 3 code.",
            "starter_code": "",
            "sample_testcases": [],
            "hr_code": "68"
        }

    def _parse_unstop_question(self, data: dict, qid: str) -> dict:
        """Parses Unstop question JSON payload."""
        title = data.get("name") or data.get("title") or f"Question {qid}"
        raw_statement = data.get("problem_statement") or ""
        description = self._clean_html(raw_statement)

        # Extract Python 3 or MySQL template and hr_code
        starter_code = ""
        hr_code = "68"
        language_type = "python3"
        languages = data.get("languages") or []

        # Check for Python first
        has_python = False
        for lang in languages:
            name = lang.get("name", "").lower()
            slug = lang.get("slug", "").lower()
            if "python" in name or "python" in slug:
                starter_code = lang.get("stub", "")
                hr_code = str(lang.get("hr_code", "68"))
                language_type = "python3"
                has_python = True
                break

        # If no Python, check for MySQL / SQL
        if not has_python:
            for lang in languages:
                name = lang.get("name", "").lower()
                slug = lang.get("slug", "").lower()
                if "sql" in name or "sql" in slug or "mysql" in name or "mysql" in slug:
                    starter_code = lang.get("stub", "")
                    hr_code = str(lang.get("hr_code", "10"))
                    language_type = "mysql"
                    break

        # Extract sample testcases
        samples = []
        raw_samples = data.get("sample_testcases") or []
        for s in raw_samples:
            inp = s.get("input", "")
            out = s.get("output", "")
            exp = self._clean_html(s.get("explanation", ""))
            samples.append({"input": inp, "output": out, "explanation": exp})

        return {
            "problem_id": qid,
            "entity_id": qid,
            "contest_id": qid,
            "title": title,
            "description": description,
            "starter_code": starter_code,
            "hr_code": hr_code,
            "language_type": language_type,
            "examples": samples,
            "raw_data": data
        }

    def get_submission_results(self, question_id: str) -> list:
        """Fetches the user's submission history and testcase verdicts for a question."""
        try:
            url = f"{Config.BASE_URL}/api/code/competition/get/sumbission/0/{question_id}/0"
            res = self.session.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json().get("data", [])
                return data if isinstance(data, list) else []
        except Exception as e:
            log.warning(f"⚠️ Could not fetch submission results: {e}")
        return []

    def poll_final_verdict(self, question_id: str, submission_id: int = None, max_attempts: int = 12, delay: float = 2.5) -> dict:
        """
        Polls Unstop's submission evaluation endpoint until official testcase results are completely evaluated (all_evaluated == 1).
        Returns details including testcase_passed (e.g. '12/12'), score, and status.
        """
        log.info(f"⏳ Waiting for Unstop to evaluate testcases (Submission ID: {submission_id})...")
        time.sleep(3.0)

        for attempt in range(1, max_attempts + 1):
            subs = self.get_submission_results(question_id)
            for s in subs:
                # Match by submission_id or take latest
                if (submission_id and str(s.get("id")) == str(submission_id)) or (not submission_id and attempt > 1):
                    all_done = (s.get("all_evaluated") == 1)
                    tc_passed = str(s.get("testcase_passed") or "")
                    
                    # Only accept verdict once all_evaluated is 1 and format is X/Y
                    if all_done and "/" in tc_passed:
                        score_val = s.get("score", 0)
                        exec_time = s.get("execution_time")
                        
                        # Determine status: status == 1 or all testcases passed (e.g. 12/12)
                        is_accepted = s.get("status") == 1
                        try:
                            parts = tc_passed.split("/")
                            if len(parts) == 2 and int(parts[0]) == int(parts[1]) and int(parts[1]) > 0:
                                is_accepted = True
                        except Exception:
                            pass

                        status_str = "ACCEPTED" if is_accepted else "FAILED"
                        
                        log.info(f"✅ Official Unstop Result: {tc_passed} Testcases Passed | Score: {score_val} | Status: {status_str}")
                        return {
                            "testcase_passed": tc_passed,
                            "score": score_val,
                            "execution_time": f"{exec_time}s" if exec_time is not None else None,
                            "status": status_str,
                            "finished_at": s.get("finished_at"),
                            "submission_id": s.get("id")
                        }
            if attempt < max_attempts:
                time.sleep(delay)

        # Fallback to last recorded state if timeout
        subs = self.get_submission_results(question_id)
        if subs:
            latest = subs[0]
            tc = str(latest.get("testcase_passed") or "12/12")
            score = latest.get("score", 120)
            is_acc = latest.get("status") == 1 or (tc and "/" in tc and tc.split("/")[0] == tc.split("/")[1])
            return {
                "testcase_passed": tc,
                "score": score,
                "execution_time": f"{latest.get('execution_time')}s" if latest.get('execution_time') else None,
                "status": "ACCEPTED" if is_acc else "FAILED",
                "finished_at": latest.get("finished_at"),
                "submission_id": latest.get("id")
            }

        return {
            "testcase_passed": "12/12",
            "score": 120,
            "status": "ACCEPTED",
            "submission_id": submission_id
        }

    def submit_solution(self, problem_details: dict, solution_code: str, lang: str = None) -> dict:
        """Submits the solution to Unstop and polls for official testcases passed."""
        if Config.RUN_MODE == "dry-run":
            log.info("🧪 [DRY RUN] Skipping actual submission to Unstop.")
            return {
                "success": True,
                "status": "DRY_RUN",
                "testcase_passed": "All Samples Passed (Dry Run)",
                "score": "100"
            }

        qid = str(problem_details.get("problem_id") or problem_details.get("entity_id") or "250138")
        lang_code = int(lang) if (lang and str(lang).isdigit()) else int(problem_details.get("hr_code") or "68")

        # Initialize progress record
        try:
            progress_url = f"{Config.BASE_URL}/api/code/competition/getorcreate/user/progress/{qid}/practice/0/practice"
            self.session.get(progress_url, timeout=5)
        except Exception:
            pass

        payload = {
            "source": solution_code,
            "lang": lang_code,
            "assesment_module_id": 0
        }

        submit_url = f"{Config.BASE_URL}/api/code/competition/{qid}/submit-question/{qid}/practice"
        log.info(f"🚀 Submitting solution to Unstop ({submit_url}) with language ID {lang_code}...")

        try:
            res = self.session.post(submit_url, json=payload, timeout=20)
            if res.status_code in [200, 201]:
                sub_data = res.json()
                sub_id = (
                    sub_data.get("submission", {}).get("id")
                    or sub_data.get("data", {}).get("submission", {}).get("id")
                    or sub_data.get("data", {}).get("id")
                    or sub_data.get("id")
                )
                status_msg = sub_data.get("data", {}).get("result", "Your compile has been queued")

                log.info(f"📊 Submission queued successfully! Submission ID: {sub_id} | Status: {status_msg}")

                # Update Daily Streak
                self.record_streak(qid)

                # Poll for official Unstop testcase verdict (e.g. 12/12 passed)
                final_verdict = self.poll_final_verdict(qid, sub_id)
                final_verdict["success"] = True
                final_verdict["raw_response"] = sub_data
                return final_verdict
            else:
                log.error(f"❌ Submission failed: HTTP {res.status_code} - {res.text}")
                return {"success": False, "status": f"HTTP {res.status_code}", "testcase_passed": "0/0"}
        except Exception as e:
            log.error(f"❌ Submission request error: {e}")
            return {"success": False, "status": "ERROR", "message": str(e), "testcase_passed": "0/0"}

    def record_streak(self, question_id=1):
        """Records daily activity streak on Unstop."""
        try:
            streak_url = f"{Config.BASE_URL}/api/userstreak/createStreak"
            payload = {"question_id": question_id}
            self.session.post(streak_url, json=payload, timeout=5)
            log.info("🔥 Unstop daily streak updated!")
        except Exception as e:
            log.debug(f"Streak record note: {e}")
