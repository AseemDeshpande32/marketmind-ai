# MarketMind AI - News API Integration

## Example Response Format

### Successful Response (GET /api/news)

```json
{
  "success": true,
  "data": [
    {
      "title": "Sensex Surges 500 Points as IT Stocks Rally",
      "description": "Indian stock markets witnessed a strong rally on Tuesday, with the benchmark Sensex gaining over 500 points driven by robust buying in IT and banking stocks.",
      "source": "Economic Times",
      "url": "https://economictimes.indiatimes.com/markets/stocks/news/sensex-surges-500-points/articleshow/123456789.cms",
      "published_at": "2026-01-22T10:30:00+05:30",
      "image_url": "https://example.com/images/market-rally.jpg"
    },
    {
      "title": "RBI Keeps Repo Rate Unchanged at 6.5%",
      "description": "Reserve Bank of India maintains status quo on key policy rates in its monetary policy review, focusing on inflation management.",
      "source": "Moneycontrol",
      "url": "https://moneycontrol.com/news/business/rbi-policy-rate-unchanged-123456.html",
      "published_at": "2026-01-22T09:15:00+05:30",
      "image_url": "https://example.com/images/rbi-policy.jpg"
    },
    {
      "title": "Tata Motors Shares Jump 5% on Strong Q3 Results",
      "description": "Tata Motors reports better-than-expected quarterly earnings, boosting investor sentiment.",
      "source": "Business Standard",
      "url": "https://business-standard.com/markets/tata-motors-shares-jump-123456.html",
      "published_at": "2026-01-22T08:45:00+05:30",
      "image_url": null
    }
  ],
  "count": 3
}
```

### Empty Response (No News Available)

```json
{
  "success": true,
  "data": [],
  "count": 0,
  "message": "No news articles available at the moment"
}
```

### Error Response (API Failure)

```json
{
  "success": false,
  "data": [],
  "count": 0,
  "error": "Unable to connect to news service"
}
```

### Error Response (Rate Limit)

```json
{
  "success": false,
  "data": [],
  "count": 0,
  "error": "Rate limit exceeded, please try again later"
}
```

### Error Response (Configuration Issue)

```json
{
  "success": false,
  "error": "News service is not configured properly",
  "message": "Please contact system administrator"
}
```

## API Endpoints

### 1. Get Latest News
- **Endpoint:** `GET /api/news`
- **Query Parameters:**
  - `category` (optional): Filter by category (e.g., 'stocks', 'markets')
  - `limit` (optional): Number of articles (1-100, default: 20)
- **Status Codes:**
  - `200`: Success
  - `400`: Invalid parameters
  - `500`: Server error
  - `503`: Service unavailable

### 2. Health Check
- **Endpoint:** `GET /api/news/health`
- **Status Codes:**
  - `200`: Service configured and healthy
  - `503`: Service not configured

## Request Examples

### Basic Request
```bash
curl http://localhost:5000/api/news
```

### With Query Parameters
```bash
curl "http://localhost:5000/api/news?category=stocks&limit=10"
```

### Health Check
```bash
curl http://localhost:5000/api/news/health
```

## Response Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | Article headline |
| `description` | string | No | Article summary or excerpt |
| `source` | string | Yes | News source/publisher name |
| `url` | string | Yes | Full article URL |
| `published_at` | string | No | ISO 8601 datetime string |
| `image_url` | string | No | Featured image URL |

## Security Features

1. **API Key Protection:**
   - API key stored securely in `.env` file
   - Never exposed in API responses
   - Loaded via environment variables

2. **Error Handling:**
   - Graceful degradation on API failures
   - User-friendly error messages
   - Detailed logging for debugging

3. **Rate Limiting:**
   - Handles external API rate limits
   - Returns appropriate HTTP status codes

4. **Input Validation:**
   - Query parameter validation
   - Limit constraints (1-100)

## Configuration

Add these to your `.env` file:

```env
NEWS_API_KEY=your-actual-api-key-here
NEWS_API_URL=https://api.yournewsprovider.com/v1/news
```

## Notes

- The service adapts to different News API response formats
- Automatically cleans and normalizes data
- Handles timeouts (10-second default)
- Supports various date formats
- Image URLs are optional
