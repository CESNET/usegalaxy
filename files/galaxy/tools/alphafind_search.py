#!/usr/bin/env python3
"""
AlphaFind API Client

Search AlphaFold protein structures for structural similarity via the AlphaFind API.

Usage:
    python3 alphafind_search.py --query P0A6F5 --output results.csv

Search Features:
    - Query by UniProt protein ID
    - Multiple index types: chains, chains_90, chains_80, chains_70, domains
    - Filters: organism, taxonomy ID, gene name, CATH annotation (domains)
    - Two modes (--mode):
        fast (default): one blocking POST /api/search-knn call; approximate
            kNN results without TM-scores or experimental-structure mapping
        full: asynchronous search, paging through all results and waiting
            for lazy TM-score computation on every page
    - Pagination and sorting support

Output:
    CSV file with structural similarity results (full mode adds TM-scores,
    alignment metrics and experimental-structure mapping)

API Limitations:
    - Maximum 5,000 results per query (hard limit)
    - Page size limited to 100 results by the API
    - TM-score calculations can take time for large result sets

Common Use Cases:
    1. Basic search for similar structures: --query P0A6F5
    2. Filter by organism: --filters '{"organism": "Mycobacterium tuberculosis"}'
    3. Sort by TM-score: --sort-by tm_score --sort-order desc
    4. Get more results: --options '{"size": 5000}' (max API limit)

For queries with >5000 results, split by organism or tax_id and combine.

Version: 1.2.1
"""

__version__ = "1.2.1"

import argparse
import csv
import json
import logging
import re
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import requests

# ============================================================================
# Constants
# ============================================================================

# Exit codes
EXIT_SUCCESS = 0
EXIT_SEARCH_FAILED = 1
EXIT_TIMEOUT = 2
EXIT_HTTP_ERROR = 3
EXIT_INTERRUPTED = 4
EXIT_UNEXPECTED_ERROR = 5

# API defaults
DEFAULT_BASE_URL = "https://alphafind.ics.muni.cz"
DEFAULT_PAGE_SIZE = 100
DEFAULT_TIMEOUT = 3600
DEFAULT_POLL_INTERVAL = 5

# Pause between page-polling rounds while scores are computed
SCORE_POLL_INTERVAL = 5

# Pagination: API max is 100 per page
MAX_PAGE_SIZE = 100

# Result limits
MAX_RESULTS_PER_QUERY = 5000

# Sort options
DEFAULT_SORT_BY = 'knn'
DEFAULT_SORT_ORDER = 'desc'
VALID_SORT_BY = ['knn', 'tm_score']
VALID_SORT_ORDER = ['asc', 'desc']

# Search modes: fast = synchronous kNN only (/api/search-knn);
# full = async search + lazy TM-scores + experimental-structure mapping
MODE_FAST = 'fast'
MODE_FULL = 'full'
VALID_MODES = [MODE_FAST, MODE_FULL]
DEFAULT_MODE = MODE_FAST

# Index types
VALID_INDEXES = ['chains', 'chains_90', 'chains_80', 'chains_70', 'domains']

# CSV output columns
CSV_COLUMNS = [
    'query_id', 'index_type', 'page_number',
    'target_id', 'score', 'organism', 'tax_id',
    'gene_name', 'protein_name', 'avg_plddt',
    'tm_score_query', 'tm_score_target', 'rmsd',
    'sequential_identity', 'aligned_residues',
    'status', 'created_at', 'completed_at',
    'has_experimental_structure', 'pdb_ids',
    'chopping'
]

# CSV output columns for fast mode (search-knn returns only kNN metadata)
FAST_CSV_COLUMNS = [
    'query', 'index_type',
    'target_id', 'score', 'organism', 'tax_id',
    'gene_name', 'protein_name', 'avg_plddt'
]
# Extra fast-mode columns for the domains index (`domain` = source TED ID)
FAST_DOMAIN_CSV_COLUMNS = ['chopping', 'cath_annotation', 'domain']

# Status constants (per-page when reading results; also per-search)
STATUS_PENDING = 'pending'
STATUS_SCORING = 'scoring'
STATUS_COMPLETED = 'completed'
STATUS_FAILED = 'failed'
STATUS_FINAL = (STATUS_COMPLETED, STATUS_FAILED)
# Client-side status: the server answers a search whose filters match nothing
# with status 'failed' plus this error. That is a valid empty result, not a
# failure, so it is reported as STATUS_NO_MATCH.
STATUS_NO_MATCH = 'no_match'
NO_MATCH_ERROR = 'No candidates matched the given filters'


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class SearchConfig:
    """Configuration for a search operation."""
    query: str
    index: str  # Required
    filters: Dict[str, Any]
    options: Dict[str, Any]
    output_file: str
    base_url: str
    poll_interval: int
    timeout: int
    page_size: int
    sort_by: str = DEFAULT_SORT_BY
    sort_order: str = DEFAULT_SORT_ORDER
    verbose: bool = False
    dry_run: bool = False
    quiet: bool = False
    mode: str = DEFAULT_MODE


class SearchFailedError(RuntimeError):
    """The API reported the search itself as failed (maps to EXIT_SEARCH_FAILED)."""


# ============================================================================
# API Client
# ============================================================================

class AlphaFindClient:
    """Client for interacting with the AlphaFind API."""

    def __init__(self, base_url: str, timeout: int = 30):
        """Initialize the AlphaFind client.

        Args:
            base_url: Base URL of the AlphaFind API
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

    def health_check(self) -> bool:
        """Check if the API is accessible.

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/health",
                timeout=self.timeout
            )
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logging.warning(f"Health check failed: {e}")
            return False

    def submit_search(
        self,
        query: str,
        index: str,
        filters: Dict[str, Any],
        options: Dict[str, Any]
    ) -> Tuple[str, str, str]:
        """Submit a search query to the API.

        Args:
            query: Protein ID to search for
            index: Index type to search
            filters: Filter criteria
            options: Search options

        Returns:
            Tuple of (query_id, index_type, status)

        For the `domains` index with a UniProt accession (rather than a
        `<ACC>_TEDnn` identifier) the API needs a chains index to resolve the
        protein to its TED domains, so the submission includes both. The
        discovery response carries `domain_ids` mapping each TED ID to its own
        per-domain query ID.

        Raises:
            requests.HTTPError: If the API request fails
        """
        effective_index = [index]
        if index == "domains" and not self._is_domain_query(query):
            effective_index = ["chains", index]

        payload = {
            "query": query,
            "index": effective_index,
            "filters": filters,
            "options": options
        }

        logging.info(f"Submitting search for query: {query}, index: {index}")
        logging.info(f"API URL: {self.base_url}/api/search")
        logging.info(f"API Payload: {json.dumps(payload)}")

        response = self.session.post(
            f"{self.base_url}/api/search",
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()
        query_id = data['id']
        index_type = data['index_type'][0]
        status = data['status']

        logging.info(f"Search submitted: query_id={query_id}, "
                    f"index_type={index_type}, status={status}")
        logging.debug(f"Response: {json.dumps(data, indent=2)}")

        return query_id, index_type, status

    # Regex matching TED domain identifiers: UniProt accession + _TEDnn
    _TED_QUERY_RE = re.compile(r'^[A-Z0-9]+_TED\d{2}$')

    @classmethod
    def _is_domain_query(cls, query: str) -> bool:
        """True if `query` is already a concrete TED domain identifier."""
        return bool(cls._TED_QUERY_RE.match(query))

    def get_domain_queries(
        self,
        query: str,
        filters: Dict[str, Any],
        options: Dict[str, Any]
    ) -> List[Tuple[str, str, str]]:
        """Resolve a `domains`-index search to one query per TED domain.

        For a UniProt accession this submits a mixed (chains+domains) POST so
        the server resolves the protein to its TED domains
        (AlphaFind sub-domains each protein into potentially several domains;
        the response's `domain_ids` maps each TED ID to its own query ID).
        For an already-resolved `<ACC>_TEDnn` identifier it submits directly.

        Returns:
            List of (ted_id, domain_query_id, status) tuples, one per domain.
        """
        response = self.session.post(
            f"{self.base_url}/api/search",
            json={
                "query": query,
                "index": ["domains"] if self._is_domain_query(query) else ["chains", "domains"],
                "filters": filters,
                "options": options
            },
            timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        domain_ids = data.get('domain_ids')
        if domain_ids:
            # Confirmed server behavior: when the protein has no TED domains,
            # `domain_ids` contains one bogus entry keyed by the bare query
            # accession itself (no _TEDnn suffix), pointing at a query that
            # produces no domains results. Detect this and return [], rather
            # than treating the bogus id as a searchable TED domain.
            if (len(domain_ids) == 1 and
                    not self._is_domain_query(next(iter(domain_ids)))):
                ted = next(iter(domain_ids))
                if ted.upper() == query.upper():
                    logging.info(
                        f"Protein '{query}' has no TED domains to search "
                        f"(server echoed the accession back as domain_ids)."
                    )
                    return []
        else:
            # Resolved-TED direct submission (the id echoes the TED id), or
            # no domain_ids key at all — use the query itself as the TED id.
            domain_ids = {data.get('query', query): data['id']}

        logging.info(
            f"Resolved '{query}' to {len(domain_ids)} TED domain(s): "
            f"{', '.join(sorted(domain_ids))}"
        )
        return [
            (ted_id, domain_query_id, data.get('status', STATUS_PENDING))
            for ted_id, domain_query_id in sorted(domain_ids.items())
        ]

    def get_results(
        self,
        query_id: str,
        index_type: str,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        sort_by: str = DEFAULT_SORT_BY,
        sort_order: str = DEFAULT_SORT_ORDER
    ) -> Dict[str, Any]:
        """Retrieve paginated search results.

        Args:
            query_id: Query ID from search submission
            index_type: Index type
            page: Page number (1-indexed)
            page_size: Number of results per page (max 100)
            sort_by: Sort field ('knn' or 'tm_score')
            sort_order: Sort order ('desc' or 'asc')

        Returns:
            Dictionary containing results and metadata

        Raises:
            requests.HTTPError: If the API request fails
        """
        params = {
            "page": page,
            "page_size": page_size,
            "sort_by": sort_by,
            "sort_order": sort_order
        }

        logging.debug(f"Fetching results: page={page}, page_size={page_size}")

        response = self.session.get(
            f"{self.base_url}/api/search/{query_id}/{index_type}/results",
            params=params,
            timeout=self.timeout
        )

        # Handle 404 responses that contain error messages
        if response.status_code == 404:
            try:
                error_data = response.json()
                if error_data.get('status') == STATUS_FAILED:
                    error_message = error_data.get('message', 'Search query not found')
                    sys.stderr.write(f"ERROR: {error_message}\n")
                    sys.stderr.flush()
                    raise RuntimeError(f"Search failed: {error_message}")
            except (ValueError, KeyError):
                # If response is not JSON or doesn't have expected structure
                sys.stderr.write(f"ERROR: Search query not found for query_id: {query_id}, index_type: {index_type}\n")
                sys.stderr.flush()
                raise RuntimeError(f"Search query not found: query_id={query_id}, index_type={index_type}")

        response.raise_for_status()

        return response.json()

    def wait_for_completion(
        self,
        query_id: str,
        index_type: str,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
        timeout: int = DEFAULT_TIMEOUT,
        show_progress: bool = True
    ) -> str:
        """Poll the API until the kNN pass has finished.

        Per the API docs the kNN pass is done once `total_results > 0`; the
        page may still report `scoring` while TM-scores are computed lazily,
        which `get_scored_results` handles. A final status ('completed' or
        'failed') also ends the wait, covering searches with zero results.

        Args:
            query_id: Query ID to monitor
            index_type: Index type
            poll_interval: Seconds between polls
            timeout: Maximum time to wait in seconds
            show_progress: Whether to show progress indicator

        Returns:
            Last reported status ('completed', 'failed', or 'scoring' etc.
            when kNN results are already available), or STATUS_NO_MATCH
            when the server reports that no candidates matched the filters

        Raises:
            TimeoutError: If timeout is exceeded
        """
        start_time = time.time()
        status = STATUS_PENDING

        logging.info(f"Waiting for completion (timeout={timeout}s, "
                    f"poll_interval={poll_interval}s)")

        while time.time() - start_time < timeout:
            try:
                response = self.get_results(query_id, index_type, page=1, page_size=1)
                status = response.get('status', STATUS_PENDING)
                total_results = response.get('total_results', 0)

                if show_progress:
                    sys.stdout.write(f"\r  Status: {status} | "
                                    f"Elapsed: {int(time.time() - start_time)}s | "
                                    f"Results: {total_results}")
                    sys.stdout.flush()

                if (status == STATUS_FAILED and
                        NO_MATCH_ERROR in str(response.get('error', ''))):
                    status = STATUS_NO_MATCH
                if (status in STATUS_FINAL or status == STATUS_NO_MATCH or
                        total_results > 0):
                    if show_progress:
                        sys.stdout.write('\n')
                    logging.info(f"kNN search finished with status: {status}, "
                                 f"total_results: {total_results}")
                    return status

                time.sleep(poll_interval)

            except requests.RequestException as e:
                logging.warning(f"Polling error (will retry): {e}")
                time.sleep(poll_interval)

        if show_progress:
            sys.stdout.write('\n')
        raise TimeoutError(
            f"Search did not complete within {timeout} seconds. "
            f"Last status: {status}"
        )

    def get_all_results(
        self,
        query_id: str,
        index_type: str,
        page_size: int = DEFAULT_PAGE_SIZE,
        sort_by: str = DEFAULT_SORT_BY,
        sort_order: str = DEFAULT_SORT_ORDER,
        show_progress: bool = True
    ) -> List[Dict[str, Any]]:
        """Fetch all paginated results.

        Args:
            query_id: Query ID
            index_type: Index type
            page_size: Number of results per page
            sort_by: Sort field
            sort_order: Sort order
            show_progress: Whether to show progress

        Returns:
            List of all result dictionaries
        """
        all_results: List[Dict[str, Any]] = []
        page = 1
        total_pages = 1

        logging.info(f"Fetching all results with page_size={page_size}")

        while page <= total_pages:
            try:
                response = self.get_results(
                    query_id, index_type,
                    page=page,
                    page_size=page_size,
                    sort_by=sort_by,
                    sort_order=sort_order
                )

                results = response.get('results', [])
                all_results.extend(results)

                if page == 1:
                    total_pages = response.get('total_pages', 1)

                if show_progress:
                    sys.stdout.write(f"\r  Fetching page {page}/{total_pages}")
                    sys.stdout.flush()

                page += 1

            except requests.RequestException as e:
                logging.error(f"Error fetching page {page}: {e}")
                break

        if show_progress:
            sys.stdout.write('\n')
        logging.info(f"Fetched {len(all_results)} results")

        return all_results


    def get_scored_results(
        self,
        query_id: str,
        index_type: str,
        page_size: int = DEFAULT_PAGE_SIZE,
        sort_by: str = DEFAULT_SORT_BY,
        sort_order: str = DEFAULT_SORT_ORDER,
        timeout: int = DEFAULT_TIMEOUT,
        poll_interval: int = SCORE_POLL_INTERVAL,
        show_progress: bool = True
    ) -> List[Dict[str, Any]]:
        """Fetch every page, waiting until each page's TM-scores are computed.

        The API computes TM-scores lazily: a search schedules them only for
        the first few targets, and each GET on a page triggers computation for
        that page's remaining targets. To obtain scores for everything, page
        through all results once to schedule the computations, then re-poll
        pages until every page reports status 'completed'.

        Pages are always requested in kNN order (stable: kNN scores never
        change). Requesting `sort_by=tm_score` from the server while scores
        are still arriving would move targets between pages and could
        duplicate or drop rows, so the requested ordering is applied locally
        once every page is complete.

        Args:
            query_id: Query ID
            index_type: Index type
            page_size: Number of results per page
            sort_by: Sort field
            sort_order: Sort order
            timeout: Maximum total wait time in seconds (shared job budget)
            poll_interval: Seconds between page-polling rounds
            show_progress: Whether to show progress

        Returns:
            List of all result dictionaries with completed TM-scores

        Raises:
            TimeoutError: If the timeout is exceeded before all pages complete
            RuntimeError: If any page reports status 'failed'
        """
        start_time = time.time()

        def fetch(page: int) -> Dict[str, Any]:
            # Server-side order is always kNN desc (stable); see docstring.
            return self.get_results(
                query_id, index_type,
                page=page, page_size=page_size,
                sort_by=DEFAULT_SORT_BY, sort_order=DEFAULT_SORT_ORDER
            )

        # Phase 1: establish the page count from the authoritative first page
        # (total_pages may be lower than ceil(total_results / page_size)) and
        # schedule computations for pages as they are first fetched.
        first = fetch(1)
        total_pages = first.get('total_pages', 1)
        all_pages = set(range(1, total_pages + 1))

        pages: Dict[int, Dict[str, Any]] = {1: first}
        completed: Set[int] = (
            {1} if first.get('status') == STATUS_COMPLETED else set()
        )

        # Phase 2: fetch every remaining page once to schedule its
        # computations. A transient error just leaves the page for phase 3.
        for page in range(2, total_pages + 1):
            if time.time() - start_time > timeout:
                break  # phase 3 reports the timeout with the missing pages
            try:
                response = fetch(page)
            except requests.RequestException as e:
                logging.warning(f"Error fetching page {page} (will retry): {e}")
                continue
            pages[page] = response
            if response.get('status') == STATUS_COMPLETED:
                completed.add(page)
            if show_progress:
                sys.stdout.write(
                    f"\r  Scheduling TM-score computation: page {page}/{total_pages}"
                )
                sys.stdout.flush()

        # Phase 3: re-poll incomplete pages until every page reports completed
        poll_interval = max(1, poll_interval)
        while len(completed) < total_pages:
            if time.time() - start_time > timeout:
                incomplete = sorted(all_pages - completed)
                if show_progress:
                    sys.stdout.write('\n')
                raise TimeoutError(
                    f"Timed out after {int(time.time() - start_time)}s waiting for "
                    f"TM-scores on {total_pages - len(completed)}/{total_pages} "
                    f"pages (incomplete pages: {incomplete}). "
                    f"Partial scores were not written."
                )

            if show_progress:
                sys.stdout.write(
                    f"\r  Computing TM-scores: {len(completed)}/{total_pages} pages done | "
                    f"Elapsed: {int(time.time() - start_time)}s"
                )
                sys.stdout.flush()
            time.sleep(poll_interval)

            for page in sorted(all_pages - completed):
                try:
                    response = fetch(page)
                except requests.RequestException as e:
                    logging.warning(f"Polling error on page {page} (will retry): {e}")
                    continue
                pages[page] = response
                status = response.get('status', STATUS_PENDING)
                if status == STATUS_COMPLETED:
                    completed.add(page)
                elif status == STATUS_FAILED:
                    if show_progress:
                        sys.stdout.write('\n')
                    raise RuntimeError(
                        f"TM-score computation failed on page {page}/{total_pages}"
                    )

        if show_progress:
            sys.stdout.write('\n')

        # All pages completed; concatenate in kNN page order, then apply the
        # requested ordering locally.
        all_results: List[Dict[str, Any]] = []
        for page in sorted(pages):
            all_results.extend(pages[page].get('results', []))
        all_results = sort_results(all_results, sort_by, sort_order)

        logging.info(
            f"Retrieved {len(all_results)} results with completed TM-scores "
            f"across {total_pages} pages"
        )
        return all_results

    def search_knn(
        self,
        query: str,
        index: str,
        filters: Dict[str, Any],
        options: Dict[str, Any],
        timeout: int = DEFAULT_TIMEOUT
    ) -> List[Dict[str, Any]]:
        """Run a synchronous kNN-only search (POST /api/search-knn).

        Blocks until the server returns the kNN hits: no TM-scores, no
        experimental-structure mapping. Results come back in kNN-score
        descending order. One page normally holds everything (k <= 5000);
        any further pages the server reports are fetched too.

        Args:
            query: UniProt accession, or a `<ACC>_TEDnn` id for `domains`
            index: Single index name
            filters: Filter criteria
            options: Search options (e.g. {"k": 100})
            timeout: Read timeout in seconds for the blocking request

        Returns:
            List of raw result dictionaries

        Raises:
            SearchFailedError: If the API reports the search as failed
                (e.g. protein not found in the index)
            requests.HTTPError: On any other HTTP error
        """
        payload = {
            "query": query,
            "index": [index],
            "filters": filters,
            "options": options
        }
        logging.info(f"Submitting kNN search for query: {query}, index: {index}")
        logging.info(f"API Payload: {json.dumps(payload)}")

        results: List[Dict[str, Any]] = []
        page = 1
        total_pages = 1
        while page <= total_pages:
            response = self.session.post(
                f"{self.base_url}/api/search-knn",
                params={"page": page, "page_size": MAX_RESULTS_PER_QUERY},
                json=payload,
                timeout=(self.timeout, max(1, timeout))
            )
            # Failed searches come back as 4xx with {"status": "failed", "error": ...}
            if response.status_code >= 400:
                try:
                    body = response.json()
                except ValueError:
                    body = None
                if isinstance(body, dict) and body.get('status') == STATUS_FAILED:
                    message = body.get('error') or body.get('message') or 'Search failed'
                    raise SearchFailedError(message)
            response.raise_for_status()

            data = response.json()
            results.extend(data.get('results', []))
            total_pages = data.get('total_pages', 1) or 1
            page += 1

        logging.info(f"kNN search returned {len(results)} results")
        return results

    def resolve_ted_ids(
        self,
        query: str,
        filters: Dict[str, Any],
        options: Dict[str, Any]
    ) -> List[str]:
        """Resolve a `domains` query to the TED domain ids to search.

        A `<ACC>_TEDnn` id is used as-is. A bare UniProt accession needs the
        asynchronous mixed POST /api/search (see `get_domain_queries`): no
        other endpoint maps a protein to its TED domains, and search-knn
        rejects bare accessions on the domains index.
        """
        if self._is_domain_query(query):
            return [query]
        return [ted for ted, _, _ in self.get_domain_queries(query, filters, options)]


# ============================================================================
# Data Processing
# ============================================================================

def flatten_result(
    result: Dict[str, Any],
    query_id: str,
    index_type: str,
    page: int
) -> Dict[str, Any]:
    """Flatten nested result dictionary for CSV export.

    Args:
        result: Raw result from API
        query_id: Query ID for this search
        index_type: Index type for this search
        page: Page number this result came from

    Returns:
        Flattened dictionary ready for CSV export
    """
    flattened = {
        'query_id': query_id,
        'index_type': index_type,
        'page_number': page,
        'target_id': result.get('target_id'),
        'score': result.get('score'),
        'organism': result.get('organism'),
        'tax_id': result.get('tax_id'),
        'gene_name': result.get('gene_name'),
        'protein_name': result.get('protein_name'),
        'avg_plddt': result.get('avg_plddt'),
        'tm_score_query': result.get('tm_score_query'),
        'tm_score_target': result.get('tm_score_target'),
        'rmsd': result.get('rmsd'),
        'sequential_identity': result.get('sequential_identity'),
        'aligned_residues': result.get('aligned_residues'),
    }

    # Flatten metadata
    metadata = result.get('metadata', {})
    flattened['status'] = metadata.get('status')
    flattened['created_at'] = metadata.get('created_at')
    flattened['completed_at'] = metadata.get('completed_at')

    # Tag domains-index rows with the domain (TED ID) that produced them —
    # tagged by run_search with the queried domain this batch belongs to.
    if index_type == 'domains':
        flattened['domain'] = result.get('domain', result.get('target_id'))

    # Flatten experimental_structure (can be None)
    exp_structure = result.get('experimental_structure')
    if exp_structure:
        flattened['has_experimental_structure'] = exp_structure.get('has_experimental_structure')
        pdb_ids = exp_structure.get('pdb_ids')
        flattened['pdb_ids'] = ';'.join(pdb_ids) if pdb_ids else ''
    else:
        flattened['has_experimental_structure'] = None
        flattened['pdb_ids'] = ''

    flattened['chopping'] = result.get('chopping', '')

    return flattened


def flatten_fast_result(
    result: Dict[str, Any],
    query: str,
    index_type: str
) -> Dict[str, Any]:
    """Flatten a search-knn (fast mode) result for CSV export.

    Args:
        result: Raw result from /api/search-knn
        query: The query string submitted (no async query id exists)
        index_type: Index type for this search

    Returns:
        Flattened dictionary ready for CSV export
    """
    flattened = {
        'query': query,
        'index_type': index_type,
        'target_id': result.get('target_id'),
        'score': result.get('score'),
        'organism': result.get('organism'),
        'tax_id': result.get('tax_id'),
        'gene_name': result.get('gene_name'),
        'protein_name': result.get('protein_name'),
        'avg_plddt': result.get('avg_plddt'),
    }
    if index_type == 'domains':
        flattened['chopping'] = result.get('chopping', '')
        flattened['cath_annotation'] = result.get('cath_annotation', '')
        flattened['domain'] = result.get('domain', result.get('target_id'))
    return flattened


def sort_results(
    results: List[Dict[str, Any]],
    sort_by: str,
    sort_order: str
) -> List[Dict[str, Any]]:
    """Order results locally by kNN score or TM-score.

    `knn` sorts on `score`, `tm_score` on `tm_score_query`. Rows missing the
    key go last; the sort is stable, so ties keep their incoming (kNN) order.
    """
    key = 'tm_score_query' if sort_by == 'tm_score' else 'score'
    present = [r for r in results if r.get(key) is not None]
    missing = [r for r in results if r.get(key) is None]
    present.sort(key=lambda r: r[key], reverse=(sort_order == 'desc'))
    return present + missing


def results_to_csv(
    results: List[Dict[str, Any]],
    query_id: str,
    index_type: str,
    filename: str,
    page_size: int,
    mode: str = MODE_FULL
) -> int:
    """Write flattened results to CSV file.

    Args:
        results: List of raw result dictionaries
        query_id: Query ID for this search (fast mode: the query string)
        index_type: Index type for this search
        filename: Output CSV filename
        page_size: Page size used (for page number assignment; full mode)
        mode: MODE_FULL or MODE_FAST, selecting the column set

    Returns:
        Number of results written. With no results a header-only CSV is
        still written: an empty result is valid output (Galaxy relies on it).
    """
    if not results:
        logging.warning("No results found; writing a CSV with only the header")

    if mode == MODE_FAST:
        flattened_results = [
            flatten_fast_result(result, query_id, index_type)
            for result in results
        ]
        fieldnames = FAST_CSV_COLUMNS + (
            FAST_DOMAIN_CSV_COLUMNS if index_type == 'domains' else []
        )
    else:
        # Calculate page numbers and flatten all results
        flattened_results = []
        for i, result in enumerate(results):
            page = (i // page_size) + 1
            flattened_results.append(
                flatten_result(result, query_id, index_type, page)
            )

        # Domains-index rows carry an extra `domain` column with the TED ID
        fieldnames = CSV_COLUMNS + (['domain'] if index_type == 'domains' else [])

    # Write to CSV
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(flattened_results)

        logging.info(f"Wrote {len(flattened_results)} results to {filename}")
        return len(flattened_results)

    except IOError as e:
        logging.error(f"Error writing CSV file: {e}")
        raise


# ============================================================================
# Argument Parsing
# ============================================================================

def parse_json_args(arg_string: str) -> Dict[str, Any]:
    """Parse JSON string argument.

    Args:
        arg_string: JSON string to parse

    Returns:
        Parsed dictionary

    Raises:
        argparse.ArgumentTypeError: If JSON is invalid
    """
    if not arg_string:
        return {}

    try:
        return json.loads(arg_string)
    except json.JSONDecodeError as e:
        raise argparse.ArgumentTypeError(f"Invalid JSON: {e}")


def parse_arguments() -> SearchConfig:
    """Parse command-line arguments.

    Returns:
        SearchConfig with all parameters
    """
    parser = argparse.ArgumentParser(
        description='AlphaFind API Client - Search for protein structures',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic search
  python3 alphafind_search.py --query P0A6F5

  # Search with organism filter
  python3 alphafind_search.py --query Q8Y547 --filters '{"organism": "Mycobacterium tuberculosis"}'

  # Search with sorting
  python3 alphafind_search.py --query Q9SBL1 --sort-by tm_score --sort-order desc

  # Request maximum results (API limit is 5000 per query)
  python3 alphafind_search.py --query P69905 --options '{"size": 5000}' --timeout 1800
        """
    )

    # Required: query
    parser.add_argument(
        '--query',
        help='UniProt protein ID to search (e.g., "P0A6F5")'
    )

    # Required: index selection
    parser.add_argument(
        '--index',
        required=True,
        choices=VALID_INDEXES,
        help=f'Index type to search. Valid: {", ".join(VALID_INDEXES)}'
    )

    # Optional: search mode
    parser.add_argument(
        '--mode',
        choices=VALID_MODES,
        default=DEFAULT_MODE,
        help=f'{MODE_FAST}: approximate kNN results returned immediately, '
             f'without TM-scores or experimental-structure mapping; '
             f'{MODE_FULL}: wait for TM-scores on all results and include '
             f'experimental-structure mapping (slow). '
             f'Default: {DEFAULT_MODE}'
    )

    # Optional: filters
    parser.add_argument(
        '--filters',
        type=parse_json_args,
        default={},
        help='Filter criteria as JSON string (e.g., \'{"organism": "Mycobacterium tuberculosis"}\')'
    )

    # Optional: search options
    parser.add_argument(
        '--options',
        type=parse_json_args,
        default={},
        help='Search options as JSON string (e.g., \'{"size": 5000}\')'
    )

    # Optional: individual filters (for Galaxy compatibility)
    parser.add_argument(
        '--filter-organism',
        help='Filter by organism scientific name: the "Scientific name" of a '
             'species-rank taxon per UniProt taxonomy '
             '(https://www.uniprot.org/taxonomy/?query=rank:species), '
             'e.g., "Mycobacterium tuberculosis"'
    )
    parser.add_argument(
        '--filter-tax-id',
        type=int,
        help='Filter by NCBI Taxonomy ID (numeric)'
    )
    parser.add_argument(
        '--filter-gene-name',
        help='Filter by gene name exactly as AlphaFind stores it: the whole '
             'name, with the same capitalisation. Copy it from the gene_name '
             'column of earlier AlphaFind results, e.g. "gpgS", "MAP_2569c". '
             'A name taken from UniProt may not match (UniProt can list a '
             'different name than the one AlphaFind indexed).'
    )
    parser.add_argument(
        '--filter-cath-annotation',
        help='Filter by CATH annotation (only for domains index)'
    )

    # Optional: individual options (for Galaxy compatibility)
    parser.add_argument(
        '--option-k',
        type=int,
        help='Number of similar proteins to return (k parameter)'
    )

    # Optional: output
    parser.add_argument(
        '--output',
        default='results.csv',
        help='Output CSV filename (default: results.csv)'
    )

    # Optional: API configuration
    parser.add_argument(
        '--base-url',
        default=DEFAULT_BASE_URL,
        help=f'AlphaFind API base URL (default: {DEFAULT_BASE_URL})'
    )

    # Optional: timeouts and polling
    parser.add_argument(
        '--poll-interval',
        type=int,
        default=DEFAULT_POLL_INTERVAL,
        help=f'Polling interval in seconds (default: {DEFAULT_POLL_INTERVAL})'
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f'Maximum wait time in seconds (default: {DEFAULT_TIMEOUT}); '
             f'in {MODE_FAST} mode the limit for the blocking kNN request(s)'
    )

    # Optional: pagination
    parser.add_argument(
        '--page-size',
        type=int,
        default=DEFAULT_PAGE_SIZE,
        choices=range(1, MAX_PAGE_SIZE + 1),
        metavar=f'[1-{MAX_PAGE_SIZE}]',
        help=f'Results per page (default: {DEFAULT_PAGE_SIZE}, max: {MAX_PAGE_SIZE})'
    )

    # Optional: sorting
    parser.add_argument(
        '--sort-by',
        choices=VALID_SORT_BY,
        default=DEFAULT_SORT_BY,
        help=f'Sort results by (default: {DEFAULT_SORT_BY}). In {MODE_FAST} '
             f'mode there are no TM-scores, so tm_score falls back to knn.'
    )

    parser.add_argument(
        '--sort-order',
        choices=VALID_SORT_ORDER,
        default=DEFAULT_SORT_ORDER,
        help=f'Sort order (default: {DEFAULT_SORT_ORDER})'
    )

    # Mode flags
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('-q', '--quiet', action='store_true',
                       help='Suppress informational output (recommended for Galaxy automation)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without executing')
    parser.add_argument('--version', action='version', version=__version__,
                        help='Show version and exit')

    args = parser.parse_args()

    # Validate required arguments
    if not args.query and not args.dry_run:
        parser.error('--query is required')

    # Build filters from both JSON and individual params
    filters = dict(args.filters)
    if args.filter_organism:
        filters['organism'] = args.filter_organism
    if args.filter_tax_id:
        filters['tax_id'] = args.filter_tax_id
    if args.filter_gene_name:
        filters['gene_name'] = args.filter_gene_name
    if args.filter_cath_annotation:
        filters['cath_annotation'] = args.filter_cath_annotation

    # Build options from both JSON and individual params
    options = dict(args.options)
    if args.option_k:
        options['k'] = args.option_k

    return SearchConfig(
        query=args.query,
        index=args.index,
        filters=filters,
        options=options,
        output_file=args.output,
        base_url=args.base_url,
        poll_interval=args.poll_interval,
        timeout=args.timeout,
        page_size=args.page_size,
        sort_by=args.sort_by,
        sort_order=args.sort_order,
        verbose=args.verbose,
        dry_run=args.dry_run,
        quiet=args.quiet,
        mode=args.mode
    )


# ============================================================================
# Logging
# ============================================================================

def setup_logging(verbose: bool, quiet: bool = False) -> None:
    """Configure logging based on verbosity and quiet mode.

    Args:
        verbose: Whether to enable verbose logging
        quiet: Whether to suppress all informational logging (for Galaxy)
    """
    if quiet:
        logging.basicConfig(
            level=logging.ERROR,
            format='%(message)s',
            stream=sys.stderr
        )
    else:
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


def error_exit(message: str, exit_code: int = 1) -> None:
    """Print error to stderr and exit.

    Args:
        message: Error message to display
        exit_code: Exit code to return
    """
    sys.stderr.write(f"ERROR: {message}\n")
    sys.stderr.flush()
    sys.exit(exit_code)


# ============================================================================
# Main Application
# ============================================================================

def run_fast_search(client: AlphaFindClient, config: SearchConfig) -> int:
    """Execute a fast-mode search: synchronous kNN via /api/search-knn.

    TM-score sorting is impossible without TM-scores, so `sort_by=tm_score`
    silently falls back to kNN order (documented in the CLI/Galaxy help).
    For the domains index, a bare accession is resolved to its TED domains
    and each domain is searched separately, tagged with a `domain` column.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    start_time = time.time()
    if config.sort_by != 'knn':
        logging.info(f"Fast mode has no TM-scores; sorting by knn instead of "
                     f"{config.sort_by}")

    def remaining() -> int:
        return config.timeout - int(time.time() - start_time)

    def fail(message: str, exit_code: int) -> int:
        logging.error(message)
        if config.quiet:
            error_exit(message, exit_code)
        return exit_code

    if config.index == 'domains':
        ted_ids = client.resolve_ted_ids(config.query, config.filters, config.options)
        if not ted_ids:
            logging.info(
                f"Protein '{config.query}' has no TED domains to search."
            )
        results: List[Dict[str, Any]] = []
        for ted_id in ted_ids:
            if remaining() <= 0:
                return fail(
                    "Timeout budget exhausted before all domains finished. "
                    "Partial results were not written.", EXIT_TIMEOUT
                )
            domain_results = client.search_knn(
                ted_id, 'domains', config.filters, config.options,
                timeout=remaining()
            )
            for r in domain_results:
                r['domain'] = ted_id
            results.extend(sort_results(domain_results, 'knn', config.sort_order))
    else:
        results = sort_results(
            client.search_knn(
                config.query, config.index, config.filters, config.options,
                timeout=remaining()
            ),
            'knn', config.sort_order
        )

    count = results_to_csv(
        results=results,
        query_id=config.query,
        index_type=config.index,
        filename=config.output_file,
        page_size=config.page_size,
        mode=MODE_FAST
    )
    if not config.quiet:
        logging.info(f"Successfully completed. {count} results saved to {config.output_file}")
    return EXIT_SUCCESS


def run_search(client: AlphaFindClient, config: SearchConfig) -> int:
    """Execute the search workflow.

    Args:
        client: AlphaFind API client
        config: Search configuration

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    if config.mode == MODE_FAST:
        return run_fast_search(client, config)

    show_progress = not config.quiet
    start_time = time.time()
    query_id: Optional[str] = None      # set below on non-domains path
    index_type = config.index            # default; chains path re-reads server value

    # Submit the search only for the non-domains path; the domains path
    # performs its own (mixed chains+domains) submission to discover TED IDs.
    if config.index != 'domains':
        query_id, index_type, status = client.submit_search(
            query=config.query,
            index=config.index,
            filters=config.filters,
            options=config.options
        )
    else:
        status = STATUS_PENDING

    # Wait for completion if needed (non-domains path only; the domains path
    # submits its own discovery request below).
    if config.index != 'domains' and status != STATUS_COMPLETED:
        if not config.quiet:
            logging.info("Waiting for search to complete...")
        status = client.wait_for_completion(
            query_id=query_id or '',
            index_type=index_type,
            poll_interval=config.poll_interval,
            timeout=config.timeout,
            show_progress=show_progress
        )

    # Check final status (non-domains path; the domains path handles
    # per-domain failures inside its own loop below).
    if config.index != 'domains' and status == STATUS_NO_MATCH:
        logging.info("No candidates matched the given filters.")
    elif config.index != 'domains' and status == STATUS_FAILED:
        error_msg = "Search failed. No results to retrieve."
        logging.error(error_msg)
        if config.quiet:
            error_exit(error_msg, EXIT_SEARCH_FAILED)
        return EXIT_SEARCH_FAILED

    # Domains index: one UniProt protein can produce several TED domains.
    # Resolve them per the API's mixed-POST contract, then iterate each
    # domain's own query id and concatenate with a tagging `domain` column.
    if config.index == 'domains':
        domain_queries = client.get_domain_queries(
            query=config.query,
            filters=config.filters,
            options=config.options
        )
        all_results: List[Dict[str, Any]] = []
        domain_query_ids: List[str] = []
        for ted_id, domain_query_id, status in domain_queries:
            if status != STATUS_COMPLETED:
                status = client.wait_for_completion(
                    query_id=domain_query_id,
                    index_type='domains',
                    poll_interval=config.poll_interval,
                    timeout=config.timeout - int(time.time() - start_time),
                    show_progress=show_progress
                )
            if status == STATUS_NO_MATCH:
                logging.info(f"No candidates matched the filters for {ted_id}.")
                domain_query_ids.append(domain_query_id)
                continue
            if status == STATUS_FAILED:
                error_msg = (
                    f"Domain search failed for {ted_id}. "
                    "Partial results were not written."
                )
                logging.error(error_msg)
                if config.quiet:
                    error_exit(error_msg, EXIT_SEARCH_FAILED)
                return EXIT_SEARCH_FAILED
            remaining = config.timeout - int(time.time() - start_time)
            if remaining <= 0:
                error_msg = (
                    "Timeout budget exhausted before all domains finished. "
                    "Partial results were not written."
                )
                logging.error(error_msg)
                if config.quiet:
                    error_exit(error_msg, EXIT_TIMEOUT)
                return EXIT_TIMEOUT
            domain_results = client.get_scored_results(
                query_id=domain_query_id,
                index_type='domains',
                page_size=config.page_size,
                sort_by=config.sort_by,
                sort_order=config.sort_order,
                timeout=remaining,
                poll_interval=config.poll_interval,
                show_progress=show_progress
            )
            for r in domain_results:
                r['domain'] = ted_id
            all_results.extend(domain_results)
            domain_query_ids.append(domain_query_id)
        if not domain_queries:
            # No TED domains for this protein — the server can return the
            # query itself as a bogus domain_ids entry in this case.
            logging.info(
                f"Protein '{config.query}' has no TED domains to search."
            )
        # Unique id labelling the batch of resolved domain queries
        query_id = ':'.join(domain_query_ids)
    elif status == STATUS_NO_MATCH:
        all_results = []
    else:
        # Fetch all results, waiting for lazy TM-score computation to finish
        # on every page before writing. Remaining time comes from the shared
        # --timeout budget (kNN polling elapsed counts against it).
        remaining = config.timeout - int(time.time() - start_time)
        if remaining <= 0:
            error_msg = (
                "No time left to wait for TM-scores -- the --timeout budget "
                "was consumed while waiting for the kNN search. Partial "
                "scores were not written."
            )
            logging.error(error_msg)
            if config.quiet:
                error_exit(error_msg, EXIT_SEARCH_FAILED)
            return EXIT_SEARCH_FAILED

        all_results = client.get_scored_results(
            query_id=query_id,
            index_type=index_type,
            page_size=config.page_size,
            sort_by=config.sort_by,
            sort_order=config.sort_order,
            timeout=remaining,
            poll_interval=config.poll_interval,
            show_progress=show_progress
        )

    results = all_results

    # Save to CSV (header-only when empty: an empty result is valid output)
    count = results_to_csv(
        results=results,
        query_id=query_id,
        index_type=index_type,
        filename=config.output_file,
        page_size=config.page_size
    )

    if not config.quiet:
        logging.info(f"Successfully completed. {count} results saved to {config.output_file}")

    return EXIT_SUCCESS


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    config = parse_arguments()
    setup_logging(config.verbose, config.quiet)

    # Log configuration if not in quiet mode
    if not config.quiet:
        logging.info("=" * 60)
        logging.info("AlphaFind API Client")
        logging.info("=" * 60)
        logging.info(f"Query: {config.query}")
        logging.info(f"Index: {config.index}")
        logging.info(f"Mode: {config.mode}")
        logging.info(f"Filters: {config.filters}")
        logging.info(f"Options: {config.options}")
        logging.info(f"Output: {config.output_file}")
        logging.info(f"Base URL: {config.base_url}")
        logging.info(f"Timeout: {config.timeout}s, Poll interval: {config.poll_interval}s")
        logging.info(f"Page size: {config.page_size}, Sort by: {config.sort_by}, Order: {config.sort_order}")
        logging.info("=" * 60)

    if config.dry_run:
        logging.info("DRY RUN - No API calls will be made")
        logging.info(f"Query: {config.query}")
        logging.info(f"Results would be saved to: {config.output_file}")
        return EXIT_SUCCESS

    try:
        client = AlphaFindClient(config.base_url)

        # Health check (optional, just warns if fails)
        if not client.health_check() and not config.quiet:
            logging.warning("Health check failed. Continuing anyway...")

        return run_search(client, config)

    except SearchFailedError as e:
        error_msg = f"Search failed: {e}"
        logging.error(error_msg)
        if config.quiet:
            error_exit(error_msg, EXIT_SEARCH_FAILED)
        return EXIT_SEARCH_FAILED

    except requests.Timeout as e:
        error_msg = f"Request timed out: {e}"
        logging.error(error_msg)
        if config.quiet:
            error_exit(error_msg, EXIT_TIMEOUT)
        return EXIT_TIMEOUT

    except TimeoutError as e:
        error_msg = str(e)
        logging.error(error_msg)
        if config.quiet:
            error_exit(error_msg, EXIT_TIMEOUT)
        return EXIT_TIMEOUT

    except requests.HTTPError as e:
        response_text = e.response.text if e.response is not None else 'No response'
        error_msg = f"HTTP error: {e}\nResponse: {response_text}"
        logging.error(error_msg)
        if config.quiet:
            error_exit(error_msg, EXIT_HTTP_ERROR)
        return EXIT_HTTP_ERROR

    except KeyboardInterrupt:
        if not config.quiet:
            logging.info("\nInterrupted by user")
        return EXIT_INTERRUPTED

    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        logging.error(error_msg, exc_info=config.verbose)
        if config.quiet:
            error_exit(error_msg, EXIT_UNEXPECTED_ERROR)
        return EXIT_UNEXPECTED_ERROR


if __name__ == '__main__':
    sys.exit(main())
