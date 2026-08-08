"""
YouTube Data API v3 Integration & Relevance Validation Service.

IMPORTANT ARCHITECTURAL DIRECTIVE:
LLMs frequently hallucinate plausible-looking but non-existent or mismatched YouTube video IDs (e.g. returning ERD tutorial videos for English courses or dead video IDs for Operating Systems).
To prevent video accuracy regressions:
1. NEVER allow an LLM or static dictionary to fabricate unverified YouTube URLs or video IDs directly.
2. All video resources MUST be resolved via YouTube Data API v3 or validated with keyword relevance filtering.
3. If no candidate passes relevance verification or API quota is unavailable, return a guaranteed live search query URL (https://www.youtube.com/results?search_query=...).
"""

import os
import json
import sqlite3
import urllib.parse
import urllib.request
from typing import Dict, Any, Optional

CACHE_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "youtube_cache.db")


def init_youtube_cache():
    try:
        os.makedirs(os.path.dirname(CACHE_DB_PATH), exist_ok=True)
        conn = sqlite3.connect(CACHE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS youtube_cache (
                cache_key TEXT PRIMARY KEY,
                video_title TEXT,
                provider TEXT,
                video_url TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Cache init warning: {e}")


init_youtube_cache()


def build_search_query(subject: str, subtopic_title: str) -> str:
    """
    Distinct, unit-testable search query builder.
    Combines subject, subtopic, and educational terms to produce targeted search queries.
    """
    clean_subj = subject.replace("Exam", "").replace("exam", "").strip()
    clean_topic = subtopic_title.replace(clean_subj, "").replace(":", "").strip()
    query = f"{clean_subj} {clean_topic} lecture tutorial explained"
    return " ".join(query.split())


def calculate_relevance_score(subject: str, topic: str, video_title: str, description: str = "") -> float:
    """
    Keyword overlap & relevance scoring between target subject/topic and returned candidate video snippet.
    Returns float score between 0.0 and 1.0.
    """
    target_terms = set(build_search_query(subject, topic).lower().split())
    # Exclude generic terms from penalty calculation
    target_terms.difference_update({"lecture", "tutorial", "explained", "course"})

    candidate_text = f"{video_title} {description}".lower()
    if not target_terms:
        return 1.0

    matches = sum(1 for term in target_terms if term in candidate_text)
    return matches / len(target_terms)


def resolve_youtube_resource(subject: str, subtopic_title: str, candidate_title: str = "") -> Dict[str, str]:
    """
    Resolves a verified, live YouTube video resource for a given subject and topic.
    1. Checks local cache first.
    2. Calls YouTube Data API v3 search.list if YOUTUBE_API_KEY is configured.
    3. Validates video status with videos.list?part=status.
    4. Performs keyword relevance check.
    5. Returns valid video URL or clean, non-broken search fallback URL:
       https://www.youtube.com/results?search_query=...
    """
    query = build_search_query(subject, subtopic_title)
    cache_key = query.lower()

    # 1. Check local cache
    try:
        conn = sqlite3.connect(CACHE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT video_title, provider, video_url FROM youtube_cache WHERE cache_key = ?", (cache_key,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"type": "video", "title": row[0], "provider": row[1], "url": row[2]}
    except Exception:
        pass

    api_key = os.environ.get("YOUTUBE_API_KEY")
    search_fallback_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
    fallback_title = f"Search '{subject}: {subtopic_title}' on YouTube"

    if not api_key:
        # Graceful fallback: return verified live search query URL (never a dead or mismatched video ID)
        return {
            "type": "video",
            "title": candidate_title or f"Educational Tutorial: {subtopic_title}",
            "provider": "YouTube Search Results",
            "url": search_fallback_url
        }

    try:
        # 2. YouTube Data API v3 search.list call
        search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&videoEmbeddable=true&safeSearch=strict&relevanceLanguage=en&order=relevance&maxResults=5&q={urllib.parse.quote_plus(query)}&key={api_key}"
        req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        items = data.get("items", [])
        video_ids = [item["id"]["videoId"] for item in items if "id" in item and "videoId" in item["id"]]

        if not video_ids:
            return {"type": "video", "title": fallback_title, "provider": "YouTube Search", "url": search_fallback_url}

        # 3. Validate video status with videos.list?part=status,snippet
        videos_url = f"https://www.googleapis.com/youtube/v3/videos?part=status,snippet&id={','.join(video_ids)}&key={api_key}"
        req_v = urllib.request.Request(videos_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_v, timeout=5) as resp_v:
            v_data = json.loads(resp_v.read().decode('utf-8'))

        v_items = v_data.get("items", [])
        for item in v_items:
            embeddable = item.get("status", {}).get("embeddable", True)
            privacy = item.get("status", {}).get("privacyStatus", "public")
            if privacy != "public" or not embeddable:
                continue

            v_title = item.get("snippet", {}).get("title", "")
            v_desc = item.get("snippet", {}).get("description", "")
            channel = item.get("snippet", {}).get("channelTitle", "Educational Channel")
            vid_id = item["id"]

            # 4. Relevance check
            rel_score = calculate_relevance_score(subject, subtopic_title, v_title, v_desc)
            if rel_score >= 0.15:  # Sufficient keyword overlap
                verified_url = f"https://www.youtube.com/watch?v={vid_id}"
                result = {"type": "video", "title": v_title, "provider": channel, "url": verified_url}

                # 5. Cache result
                try:
                    conn = sqlite3.connect(CACHE_DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("INSERT OR REPLACE INTO youtube_cache (cache_key, video_title, provider, video_url) VALUES (?, ?, ?, ?)", (cache_key, v_title, channel, verified_url))
                    conn.commit()
                    conn.close()
                except Exception:
                    pass

                return result

    except Exception as e:
        print(f"YouTube API lookup notice: {e}")

    # Fallback to YouTube search query URL if API call fails or no candidate matches
    return {
        "type": "video",
        "title": fallback_title,
        "provider": "YouTube Search Result",
        "url": search_fallback_url
    }
