import { NextRequest, NextResponse } from 'next/server';

const SEARXNG_URL = process.env.SEARXNG_URL || 'http://localhost:8888';

interface SearchResult {
  position: number;
  title: string;
  url: string;
  snippet: string;
  engine: string;
}

export async function POST(req: NextRequest) {
  try {
    const { query, num_results = 5 } = await req.json();

    if (!query || typeof query !== 'string') {
      return NextResponse.json(
        { error: 'Query is required and must be a string' },
        { status: 400 }
      );
    }

    // Validate num_results
    const resultCount = Math.min(Math.max(parseInt(num_results), 1), 10);

    // Build SearXNG URL
    const searchUrl = new URL('/search', SEARXNG_URL);
    searchUrl.searchParams.set('q', query);
    searchUrl.searchParams.set('format', 'json');
    searchUrl.searchParams.set('language', 'en');
    searchUrl.searchParams.set('safesearch', '1');
    searchUrl.searchParams.set('categories', 'general');

    // Call SearXNG with timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);

    const response = await fetch(searchUrl.toString(), {
      headers: {
        'Accept': 'application/json',
        'User-Agent': 'AetherAI/1.0',
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`SearXNG returned status ${response.status}`);
    }

    const data = await response.json();

    // Format results
    const results: SearchResult[] = (data.results || [])
      .slice(0, resultCount)
      .map((result: any, index: number) => ({
        position: index + 1,
        title: result.title || 'No title',
        url: result.url || '',
        snippet: result.content || result.description || '',
        engine: result.engine || 'unknown',
      }))
      .filter((r: SearchResult) => r.url); // Filter out results without URLs

    return NextResponse.json({
      success: true,
      query,
      results,
      total_results: results.length,
      search_metadata: {
        timestamp: new Date().toISOString(),
        engines_used: Array.from(new Set(results.map(r => r.engine))),
        searxng_url: SEARXNG_URL,
      },
    });

  } catch (error) {
    console.error('Search API error:', error);

    const errorMessage = error instanceof Error ? error.message : 'Search failed';
    const isTimeout = errorMessage.includes('aborted');

    return NextResponse.json(
      {
        success: false,
        error: isTimeout ? 'Search request timed out' : errorMessage,
        query: null,
      },
      { status: isTimeout ? 504 : 500 }
    );
  }
}
